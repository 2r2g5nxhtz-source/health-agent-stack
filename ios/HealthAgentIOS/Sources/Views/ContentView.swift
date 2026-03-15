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

                    GroupBox("Webhook") {
                        VStack(alignment: .leading, spacing: 12) {
                            TextField("Webhook URL", text: $viewModel.webhookURLString, axis: .vertical)
                                .textInputAutocapitalization(.never)
                                .keyboardType(.URL)
                                .autocorrectionDisabled()
                                .textFieldStyle(.roundedBorder)

                            Button("Save Webhook") {
                                viewModel.saveWebhookURL()
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

    private func triggerSend() {
        Task {
            await viewModel.requestPermissionsAndSend()
        }
    }
}
