import Foundation
import HealthKit

@MainActor
final class HealthAgentViewModel: ObservableObject {
    @Published var statusMessage = "Ready"
    @Published var isLoading = false
    @Published var lastPayload: HealthPayload?
    @Published var lastWarnings: [String] = []
    @Published var sendHistory: [SendHistoryEntry]
    @Published var webhookURLString: String
    @Published var webhookSecret: String

    private let healthStore = HKHealthStore()
    private let webhookKey = "healthAgent.webhookURL"
    private let webhookSecretKey = "healthAgent.webhookSecret"
    private let sendHistoryKey = "healthAgent.sendHistory"
    private let webhookPlaceholder = "https://your-n8n-host/webhook/apple-health"
    private let simulatorWebhookURL = "http://127.0.0.1:5678/webhook/apple-health"

    init() {
        sendHistory = Self.loadSendHistory()
        #if targetEnvironment(simulator)
        webhookURLString = UserDefaults.standard.string(forKey: webhookKey) ?? simulatorWebhookURL
        #else
        webhookURLString = UserDefaults.standard.string(forKey: webhookKey) ?? ""
        #endif
        webhookSecret = UserDefaults.standard.string(forKey: webhookSecretKey) ?? ""
    }

    func saveSettings() {
        let trimmed = webhookURLString.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedSecret = webhookSecret.trimmingCharacters(in: .whitespacesAndNewlines)

        webhookURLString = trimmed
        webhookSecret = trimmedSecret

        if trimmed.isEmpty {
            UserDefaults.standard.removeObject(forKey: webhookKey)
        } else {
            UserDefaults.standard.set(trimmed, forKey: webhookKey)
        }

        if trimmedSecret.isEmpty {
            UserDefaults.standard.removeObject(forKey: webhookSecretKey)
        } else {
            UserDefaults.standard.set(trimmedSecret, forKey: webhookSecretKey)
        }
    }

    func requestPermissionsAndSend() async {
        #if targetEnvironment(simulator)
        await sendUsingSimulatorMockData()
        #else
        guard HKHealthStore.isHealthDataAvailable() else {
            statusMessage = "Health data is not available on this device."
            addHistoryEntry(status: .failed, payload: nil, warnings: [], detail: statusMessage)
            return
        }

        let trimmedWebhookURL = webhookURLString.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedWebhookURL.isEmpty else {
            statusMessage = "Enter your webhook URL before sending."
            addHistoryEntry(status: .failed, payload: nil, warnings: [], detail: statusMessage)
            return
        }

        guard trimmedWebhookURL != webhookPlaceholder else {
            statusMessage = "Replace the placeholder webhook URL with your own endpoint."
            addHistoryEntry(status: .failed, payload: nil, warnings: [], detail: statusMessage)
            return
        }

        guard let webhookURL = URL(string: trimmedWebhookURL), let scheme = webhookURL.scheme, ["http", "https"].contains(scheme) else {
            statusMessage = "Webhook URL is invalid."
            addHistoryEntry(status: .failed, payload: nil, warnings: [], detail: statusMessage)
            return
        }

        isLoading = true
        lastWarnings = []
        statusMessage = "Requesting Health access..."

        do {
            saveSettings()
            try await requestPermissions()
            statusMessage = "Collecting latest samples..."
            let result = await buildPayload()
            lastPayload = result.payload
            lastWarnings = result.warnings
            statusMessage = result.warnings.isEmpty ? "Sending payload to n8n..." : "Sending payload with warnings..."
            try await send(payload: result.payload, to: webhookURL)
            statusMessage = result.warnings.isEmpty
                ? "Sent successfully at \(result.payload.timestamp)"
                : "Sent with warnings at \(result.payload.timestamp)"
            addHistoryEntry(
                status: result.warnings.isEmpty ? .success : .warning,
                payload: result.payload,
                warnings: result.warnings,
                detail: statusMessage
            )
        } catch {
            statusMessage = error.localizedDescription
            addHistoryEntry(status: .failed, payload: lastPayload, warnings: lastWarnings, detail: statusMessage)
        }

        isLoading = false
        #endif
    }

    var webhookPrompt: String {
        webhookPlaceholder
    }

    var webhookSecretPrompt: String {
        "Optional shared secret for secure workflows"
    }

    func clearHistory() {
        sendHistory = []
        UserDefaults.standard.removeObject(forKey: sendHistoryKey)
    }

    private func requestPermissions() async throws {
        let types: Set<HKObjectType> = [
            HKQuantityType.quantityType(forIdentifier: .heartRate)!,
            HKQuantityType.quantityType(forIdentifier: .bloodGlucose)!,
            HKQuantityType.quantityType(forIdentifier: .bodyMass)!,
            HKCategoryType.categoryType(forIdentifier: .sleepAnalysis)!
        ]

        try await healthStore.requestAuthorization(toShare: [], read: types)
    }

    #if targetEnvironment(simulator)
    private func sendUsingSimulatorMockData() async {
        let trimmedWebhookURL = webhookURLString.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedWebhookURL.isEmpty else {
            statusMessage = "Enter your webhook URL before sending."
            addHistoryEntry(status: .failed, payload: nil, warnings: [], detail: statusMessage)
            return
        }

        guard let webhookURL = URL(string: trimmedWebhookURL), let scheme = webhookURL.scheme, ["http", "https"].contains(scheme) else {
            statusMessage = "Webhook URL is invalid."
            addHistoryEntry(status: .failed, payload: nil, warnings: [], detail: statusMessage)
            return
        }

        isLoading = true
        lastWarnings = []
        statusMessage = "Using simulator mock health data..."

        do {
            saveSettings()
            let result = buildSimulatorMockPayload()
            lastPayload = result.payload
            lastWarnings = result.warnings
            statusMessage = "Sending simulator payload to n8n..."
            try await send(payload: result.payload, to: webhookURL)
            statusMessage = "Sent simulator payload successfully at \(result.payload.timestamp)"
            addHistoryEntry(status: .success, payload: result.payload, warnings: result.warnings, detail: statusMessage)
        } catch {
            statusMessage = error.localizedDescription
            addHistoryEntry(status: .failed, payload: lastPayload, warnings: lastWarnings, detail: statusMessage)
        }

        isLoading = false
    }

    private func buildSimulatorMockPayload() -> PayloadResult {
        let payload = HealthPayload(
            heartRate: 92,
            glucose: 118,
            weight: 81.4,
            sleepHours: 5.6,
            timestamp: ISO8601DateFormatter().string(from: Date())
        )

        return PayloadResult(
            payload: payload,
            warnings: ["Simulator mode uses mock Apple Health data."]
        )
    }
    #endif

    private func buildPayload() async -> PayloadResult {
        async let heartRateResult = latestHeartRate()
        async let glucoseResult = latestBloodGlucose()
        async let weightResult = latestBodyMass()
        async let sleepHoursResult = totalSleepHoursForLast24Hours()

        let heartRate = await heartRateResult
        let glucose = await glucoseResult
        let weight = await weightResult
        let sleepHours = await sleepHoursResult

        let warnings = [heartRate.warning, glucose.warning, weight.warning, sleepHours.warning].compactMap { $0 }
        let payload = HealthPayload(
            heartRate: heartRate.value,
            glucose: glucose.value,
            weight: weight.value,
            sleepHours: sleepHours.value,
            timestamp: ISO8601DateFormatter().string(from: Date())
        )

        return PayloadResult(payload: payload, warnings: warnings)
    }

    private func latestHeartRate() async -> SampleResult<Double> {
        let type = HKQuantityType.quantityType(forIdentifier: .heartRate)!
        do {
            let sample = try await latestQuantitySample(for: type)
            let value = sample.quantity.doubleValue(for: HKUnit.count().unitDivided(by: .minute()))
            return .init(value: value, warning: nil)
        } catch {
            return .init(value: nil, warning: "Heart rate sample not available.")
        }
    }

    private func latestBloodGlucose() async -> SampleResult<Double> {
        let type = HKQuantityType.quantityType(forIdentifier: .bloodGlucose)!
        do {
            let sample = try await latestQuantitySample(for: type)
            let unit = HKUnit.gramUnit(with: .milli).unitDivided(by: HKUnit.literUnit(with: .deci))
            let value = sample.quantity.doubleValue(for: unit)
            return .init(value: value, warning: nil)
        } catch {
            return .init(value: nil, warning: "Blood glucose sample not available.")
        }
    }

    private func latestBodyMass() async -> SampleResult<Double> {
        let type = HKQuantityType.quantityType(forIdentifier: .bodyMass)!
        do {
            let sample = try await latestQuantitySample(for: type)
            let value = sample.quantity.doubleValue(for: .gramUnit(with: .kilo))
            return .init(value: value, warning: nil)
        } catch {
            return .init(value: nil, warning: "Body mass sample not available.")
        }
    }

    private func totalSleepHoursForLast24Hours() async -> SampleResult<Double> {
        let type = HKCategoryType.categoryType(forIdentifier: .sleepAnalysis)!
        let endDate = Date()
        let startDate = Calendar.current.date(byAdding: .day, value: -1, to: endDate)!
        let predicate = HKQuery.predicateForSamples(withStart: startDate, end: endDate)
        let sort = NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: false)

        do {
            let samples = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<[HKCategorySample], Error>) in
                let query = HKSampleQuery(sampleType: type, predicate: predicate, limit: HKObjectQueryNoLimit, sortDescriptors: [sort]) { _, samples, error in
                    if let error {
                        continuation.resume(throwing: error)
                        return
                    }

                    let categorySamples = (samples as? [HKCategorySample]) ?? []
                    continuation.resume(returning: categorySamples)
                }

                healthStore.execute(query)
            }

            let sleepValues: Set<Int> = [
                HKCategoryValueSleepAnalysis.asleepUnspecified.rawValue,
                HKCategoryValueSleepAnalysis.asleepCore.rawValue,
                HKCategoryValueSleepAnalysis.asleepDeep.rawValue,
                HKCategoryValueSleepAnalysis.asleepREM.rawValue
            ]

            let totalSeconds = samples
                .filter { sleepValues.contains($0.value) }
                .reduce(0.0) { partial, sample in
                    partial + sample.endDate.timeIntervalSince(sample.startDate)
                }

            guard totalSeconds > 0 else {
                return .init(value: nil, warning: "Sleep samples were found, but no asleep segments were available.")
            }

            return .init(value: (totalSeconds / 3600.0 * 10).rounded() / 10, warning: nil)
        } catch {
            return .init(value: nil, warning: "Sleep analysis sample not available.")
        }
    }

    private func latestQuantitySample(for type: HKQuantityType) async throws -> HKQuantitySample {
        let sort = NSSortDescriptor(key: HKSampleSortIdentifierEndDate, ascending: false)

        return try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<HKQuantitySample, Error>) in
            let query = HKSampleQuery(sampleType: type, predicate: nil, limit: 1, sortDescriptors: [sort]) { _, samples, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }

                guard let sample = (samples as? [HKQuantitySample])?.first else {
                    continuation.resume(throwing: HealthAgentError.noSamples(type.identifier))
                    return
                }

                continuation.resume(returning: sample)
            }

            healthStore.execute(query)
        }
    }

    private func send(payload: HealthPayload, to webhookURL: URL) async throws {
        var request = URLRequest(url: webhookURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if !webhookSecret.isEmpty {
            request.setValue(webhookSecret, forHTTPHeaderField: "X-Health-Agent-Secret")
        }
        request.httpBody = try JSONEncoder().encode(payload)

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw HealthAgentError.invalidResponse
        }
    }

    private func addHistoryEntry(status: SendHistoryStatus, payload: HealthPayload?, warnings: [String], detail: String) {
        let entry = SendHistoryEntry(
            recordedAt: ISO8601DateFormatter().string(from: Date()),
            status: status,
            detail: detail,
            payload: payload.map(SendHistoryPayload.init),
            warnings: warnings
        )

        sendHistory.insert(entry, at: 0)
        sendHistory = Array(sendHistory.prefix(10))
        persistSendHistory()
    }

    private func persistSendHistory() {
        guard let data = try? JSONEncoder().encode(sendHistory) else { return }
        UserDefaults.standard.set(data, forKey: sendHistoryKey)
    }

    private static func loadSendHistory() -> [SendHistoryEntry] {
        guard
            let data = UserDefaults.standard.data(forKey: "healthAgent.sendHistory"),
            let entries = try? JSONDecoder().decode([SendHistoryEntry].self, from: data)
        else {
            return []
        }

        return entries
    }
}

struct HealthPayload: Codable, Sendable {
    let heartRate: Double?
    let glucose: Double?
    let weight: Double?
    let sleepHours: Double?
    let timestamp: String

    enum CodingKeys: String, CodingKey {
        case heartRate = "heart_rate"
        case glucose
        case weight
        case sleepHours = "sleep_hours"
        case timestamp
    }
}

struct PayloadResult: Sendable {
    let payload: HealthPayload
    let warnings: [String]
}

struct SampleResult<Value: Sendable>: Sendable {
    let value: Value?
    let warning: String?
}

enum HealthAgentError: LocalizedError {
    case noSamples(String)
    case invalidResponse

    var errorDescription: String? {
        switch self {
        case .noSamples(let identifier):
            return "No Health samples found for \(identifier)."
        case .invalidResponse:
            return "Webhook did not return a 2xx response."
        }
    }
}

enum SendHistoryStatus: String, Codable, Sendable {
    case success
    case warning
    case failed

    var title: String {
        switch self {
        case .success:
            return "Success"
        case .warning:
            return "Sent With Warnings"
        case .failed:
            return "Failed"
        }
    }
}

struct SendHistoryPayload: Codable, Sendable {
    let heartRate: Double?
    let glucose: Double?
    let weight: Double?
    let sleepHours: Double?
    let timestamp: String

    init(payload: HealthPayload) {
        heartRate = payload.heartRate
        glucose = payload.glucose
        weight = payload.weight
        sleepHours = payload.sleepHours
        timestamp = payload.timestamp
    }
}

struct SendHistoryEntry: Identifiable, Codable, Sendable {
    let id: UUID
    let recordedAt: String
    let status: SendHistoryStatus
    let detail: String
    let payload: SendHistoryPayload?
    let warnings: [String]

    init(
        id: UUID = UUID(),
        recordedAt: String,
        status: SendHistoryStatus,
        detail: String,
        payload: SendHistoryPayload?,
        warnings: [String]
    ) {
        self.id = id
        self.recordedAt = recordedAt
        self.status = status
        self.detail = detail
        self.payload = payload
        self.warnings = warnings
    }
}
