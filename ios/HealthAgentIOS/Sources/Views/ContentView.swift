import SwiftUI

struct ContentView: View {
    @ObservedObject var viewModel: HealthAgentViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("Health Agent")
                        .font(.largeTitle.bold())

                    Text("Reads recent Apple Health data and posts it to your private n8n webhook.")
                        .foregroundStyle(.secondary)

                    if let payload = viewModel.lastPayload {
                        GroupBox("Overview") {
                            VStack(alignment: .leading, spacing: 12) {
                                HStack(spacing: 12) {
                                    metricCard(title: "Heart Rate", value: formattedValue(payload.heartRate), tint: .red)
                                    metricCard(title: "Glucose", value: formattedValue(payload.glucose), tint: .orange)
                                }

                                HStack(spacing: 12) {
                                    metricCard(title: "Weight", value: formattedValue(payload.weight), tint: .blue)
                                    metricCard(title: "Sleep", value: formattedValue(payload.sleepHours), tint: .teal)
                                }

                                if let latestSend = viewModel.sendHistory.first {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text("Latest Send")
                                            .font(.footnote.weight(.semibold))
                                            .foregroundStyle(.secondary)

                                        Text(latestSend.status.title)
                                            .font(.headline)

                                        Text(latestSend.detail)
                                            .font(.subheadline)
                                            .foregroundStyle(.secondary)
                                    }
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }

                    GroupBox("Webhook") {
                        VStack(alignment: .leading, spacing: 12) {
                            TextField(viewModel.webhookPrompt, text: $viewModel.webhookURLString, axis: .vertical)
                                .textInputAutocapitalization(.never)
                                .keyboardType(.URL)
                                .autocorrectionDisabled()
                                .textFieldStyle(.roundedBorder)

                            SecureField(viewModel.webhookSecretPrompt, text: $viewModel.webhookSecret)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                                .textFieldStyle(.roundedBorder)

                            Text("Leave the secret empty for the basic webhook workflow. Set it when using the secure workflow.")
                                .font(.footnote)
                                .foregroundStyle(.secondary)

                            Button("Save Settings") {
                                viewModel.saveSettings()
                            }
                            .buttonStyle(.bordered)
                        }
                    }

                    Button(action: triggerSend) {
                        HStack {
                            if viewModel.isLoading {
                                ProgressView()
                                    .tint(.white)
                            }
                            Text(viewModel.isLoading ? "Sending..." : "Send Now")
                                .fontWeight(.semibold)
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                    }
                    .disabled(viewModel.isLoading)

                    GroupBox("Status") {
                        Text(viewModel.statusMessage)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }

                    if !viewModel.lastWarnings.isEmpty {
                        GroupBox("Warnings") {
                            VStack(alignment: .leading, spacing: 8) {
                                ForEach(viewModel.lastWarnings, id: \.self) { warning in
                                    Text("• \(warning)")
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }

                    if let payload = viewModel.lastPayload {
                        GroupBox("Last Payload") {
                            VStack(alignment: .leading, spacing: 8) {
                                payloadRow("heart_rate", value: payload.heartRate)
                                payloadRow("glucose", value: payload.glucose)
                                payloadRow("weight", value: payload.weight)
                                payloadRow("sleep_hours", value: payload.sleepHours)
                                Text("timestamp: \(payload.timestamp)")
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }

                    if !viewModel.sendHistory.isEmpty {
                        GroupBox("Recent Sends") {
                            VStack(alignment: .leading, spacing: 12) {
                                Button("Clear History") {
                                    viewModel.clearHistory()
                                }
                                .buttonStyle(.bordered)

                                ForEach(viewModel.sendHistory) { entry in
                                    VStack(alignment: .leading, spacing: 6) {
                                        Text(entry.status.title)
                                            .font(.headline)

                                        Text(entry.detail)
                                            .font(.subheadline)

                                        Text("recorded_at: \(entry.recordedAt)")
                                            .font(.footnote)
                                            .foregroundStyle(.secondary)

                                        if let payload = entry.payload {
                                            Text("heart_rate: \(formattedValue(payload.heartRate))")
                                                .font(.footnote)
                                            Text("glucose: \(formattedValue(payload.glucose))")
                                                .font(.footnote)
                                            Text("weight: \(formattedValue(payload.weight))")
                                                .font(.footnote)
                                            Text("sleep_hours: \(formattedValue(payload.sleepHours))")
                                                .font(.footnote)
                                        }

                                        if !entry.warnings.isEmpty {
                                            ForEach(entry.warnings, id: \.self) { warning in
                                                Text("• \(warning)")
                                                    .font(.footnote)
                                                    .foregroundStyle(.secondary)
                                            }
                                        }
                                    }
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .padding(.vertical, 4)
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("Health Agent")
        }
    }

    @ViewBuilder
    private func payloadRow(_ name: String, value: Double?) -> some View {
        if let value {
            Text("\(name): \(value.formatted(.number.precision(.fractionLength(0...1))))")
        } else {
            Text("\(name): null")
                .foregroundStyle(.secondary)
        }
    }

    private func formattedValue(_ value: Double?) -> String {
        guard let value else { return "null" }
        return value.formatted(.number.precision(.fractionLength(0...1)))
    }

    private func metricCard(title: String, value: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.footnote.weight(.semibold))
                .foregroundStyle(.secondary)

            Text(value)
                .font(.title3.weight(.bold))
                .foregroundStyle(tint)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(tint.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private func triggerSend() {
        Task {
            await viewModel.requestPermissionsAndSend()
        }
    }
}
