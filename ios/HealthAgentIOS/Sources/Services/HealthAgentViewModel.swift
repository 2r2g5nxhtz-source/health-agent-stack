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
            let ns = error as NSError
            statusMessage = "\(error.localizedDescription) [domain=\(ns.domain) code=\(ns.code)]"
            addHistoryEntry(status: .failed, payload: lastPayload, warnings: lastWarnings, detail: statusMessage)
        }

        isLoading = false
        // Now that permissions have been granted at least once, (re)register
        // background delivery so future samples post automatically.
        startBackgroundDelivery()
        #endif
    }

    /// Types HealthKit should wake the app for in the background.
    private var backgroundDeliveryTypes: [HKSampleType] {
        [
            HKQuantityType.quantityType(forIdentifier: .heartRate),
            HKQuantityType.quantityType(forIdentifier: .bloodGlucose),
            HKQuantityType.quantityType(forIdentifier: .bodyMass),
            HKCategoryType.categoryType(forIdentifier: .sleepAnalysis),
            HKQuantityType.quantityType(forIdentifier: .heartRateVariabilitySDNN),
            HKQuantityType.quantityType(forIdentifier: .restingHeartRate),
            HKQuantityType.quantityType(forIdentifier: .oxygenSaturation),
            HKQuantityType.quantityType(forIdentifier: .respiratoryRate),
            HKQuantityType.quantityType(forIdentifier: .stepCount)
        ].compactMap { $0 }
    }

    private var observerQueries: [HKObserverQuery] = []

    /// Registers HealthKit background delivery + observer queries so the app is
    /// woken when NEW health samples arrive and posts them automatically. iOS
    /// still decides the exact timing, but no manual "Send Now" tap is needed.
    /// Call once at app launch (after permissions have been granted at least once).
    func startBackgroundDelivery() {
        #if !targetEnvironment(simulator)
        guard HKHealthStore.isHealthDataAvailable() else { return }
        guard observerQueries.isEmpty else { return } // already registered

        for type in backgroundDeliveryTypes {
            healthStore.enableBackgroundDelivery(for: type, frequency: .hourly) { _, _ in }

            let query = HKObserverQuery(sampleType: type, predicate: nil) { [weak self] _, completion, _ in
                let done = UncheckedSendableBox(completion)
                Task { @MainActor in
                    await self?.sendInBackground()
                    done.value()
                }
            }
            healthStore.execute(query)
            observerQueries.append(query)
        }
        #endif
    }

    /// Silent send used by background observers — same payload/send path as the
    /// manual button, but without touching UI-facing loading state.
    private func sendInBackground() async {
        #if !targetEnvironment(simulator)
        let trimmedWebhookURL = webhookURLString.trimmingCharacters(in: .whitespacesAndNewlines)
        guard
            !trimmedWebhookURL.isEmpty,
            trimmedWebhookURL != webhookPlaceholder,
            let webhookURL = URL(string: trimmedWebhookURL),
            let scheme = webhookURL.scheme, ["http", "https"].contains(scheme)
        else { return }

        do {
            let result = await buildPayload()
            try await send(payload: result.payload, to: webhookURL)
            lastPayload = result.payload
            statusMessage = "Auto-sent at \(result.payload.timestamp)"
            addHistoryEntry(
                status: result.warnings.isEmpty ? .success : .warning,
                payload: result.payload,
                warnings: result.warnings,
                detail: statusMessage
            )
        } catch {
            let ns = error as NSError
            addHistoryEntry(status: .failed, payload: lastPayload, warnings: [], detail: "Auto-send failed: \(error.localizedDescription) [code=\(ns.code)]")
        }
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
            HKCategoryType.categoryType(forIdentifier: .sleepAnalysis)!,
            HKQuantityType.quantityType(forIdentifier: .heartRateVariabilitySDNN)!,
            HKQuantityType.quantityType(forIdentifier: .restingHeartRate)!,
            HKQuantityType.quantityType(forIdentifier: .oxygenSaturation)!,
            HKQuantityType.quantityType(forIdentifier: .respiratoryRate)!,
            HKQuantityType.quantityType(forIdentifier: .stepCount)!
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
            let ns = error as NSError
            statusMessage = "\(error.localizedDescription) [domain=\(ns.domain) code=\(ns.code)]"
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
            hrv: 30,
            restingHeartRate: 72,
            spo2: 96,
            respiratoryRate: 16,
            steps: 7000,
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
        async let hrvResult = latestHRV()
        async let restingHeartRateResult = latestRestingHeartRate()
        async let spo2Result = latestSpO2()
        async let respiratoryRateResult = latestRespiratoryRate()
        async let stepsResult = totalStepsForLast24Hours()

        let heartRate = await heartRateResult
        let glucose = await glucoseResult
        let weight = await weightResult
        let sleepHours = await sleepHoursResult
        let hrv = await hrvResult
        let restingHeartRate = await restingHeartRateResult
        let spo2 = await spo2Result
        let respiratoryRate = await respiratoryRateResult
        let steps = await stepsResult

        let warnings = [
            heartRate.warning,
            glucose.warning,
            weight.warning,
            sleepHours.warning,
            hrv.warning,
            restingHeartRate.warning,
            spo2.warning,
            respiratoryRate.warning,
            steps.warning
        ].compactMap { $0 }
        let payload = HealthPayload(
            heartRate: heartRate.value,
            glucose: glucose.value,
            weight: weight.value,
            sleepHours: sleepHours.value,
            hrv: hrv.value,
            restingHeartRate: restingHeartRate.value,
            spo2: spo2.value,
            respiratoryRate: respiratoryRate.value,
            steps: steps.value,
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

    private func latestHRV() async -> SampleResult<Double> {
        let type = HKQuantityType.quantityType(forIdentifier: .heartRateVariabilitySDNN)!
        do {
            let sample = try await latestQuantitySample(for: type)
            let value = sample.quantity.doubleValue(for: .secondUnit(with: .milli))
            return .init(value: value, warning: nil)
        } catch {
            return .init(value: nil, warning: "Heart rate variability sample not available.")
        }
    }

    private func latestRestingHeartRate() async -> SampleResult<Double> {
        let type = HKQuantityType.quantityType(forIdentifier: .restingHeartRate)!
        do {
            let sample = try await latestQuantitySample(for: type)
            let value = sample.quantity.doubleValue(for: HKUnit.count().unitDivided(by: .minute()))
            return .init(value: value, warning: nil)
        } catch {
            return .init(value: nil, warning: "Resting heart rate sample not available.")
        }
    }

    private func latestSpO2() async -> SampleResult<Double> {
        let type = HKQuantityType.quantityType(forIdentifier: .oxygenSaturation)!
        do {
            let sample = try await latestQuantitySample(for: type)
            let value = sample.quantity.doubleValue(for: .percent()) * 100
            return .init(value: value, warning: nil)
        } catch {
            return .init(value: nil, warning: "Blood oxygen (SpO2) sample not available.")
        }
    }

    private func latestRespiratoryRate() async -> SampleResult<Double> {
        let type = HKQuantityType.quantityType(forIdentifier: .respiratoryRate)!
        do {
            let sample = try await latestQuantitySample(for: type)
            let value = sample.quantity.doubleValue(for: HKUnit.count().unitDivided(by: .minute()))
            return .init(value: value, warning: nil)
        } catch {
            return .init(value: nil, warning: "Respiratory rate sample not available.")
        }
    }

    private func totalStepsForLast24Hours() async -> SampleResult<Double> {
        let type = HKQuantityType.quantityType(forIdentifier: .stepCount)!
        let endDate = Date()
        let startDate = Calendar.current.date(byAdding: .day, value: -1, to: endDate)!
        let predicate = HKQuery.predicateForSamples(withStart: startDate, end: endDate)

        do {
            let statistics = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<HKStatistics?, Error>) in
                let query = HKStatisticsQuery(quantityType: type, quantitySamplePredicate: predicate, options: .cumulativeSum) { _, statistics, error in
                    if let error {
                        continuation.resume(throwing: error)
                        return
                    }

                    continuation.resume(returning: statistics)
                }

                healthStore.execute(query)
            }

            guard let sum = statistics?.sumQuantity() else {
                return .init(value: nil, warning: "Step count sample not available.")
            }

            let value = sum.doubleValue(for: .count())
            return .init(value: value, warning: nil)
        } catch {
            return .init(value: nil, warning: "Step count sample not available.")
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

        let session = URLSession(configuration: .default, delegate: TailnetTrustDelegate(trustedHost: webhookURL.host), delegateQueue: nil)
        let (_, response) = try await session.data(for: request)

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

/// Trusts a self-signed TLS certificate ONLY for the specific host the user configured
/// as their webhook (their own Tailscale-only n8n gateway). All other hosts fall back
/// to standard system trust evaluation — this does not weaken TLS validation globally.
final class TailnetTrustDelegate: NSObject, URLSessionDelegate, URLSessionTaskDelegate {
    private let trustedHost: String?

    init(trustedHost: String?) {
        self.trustedHost = trustedHost
    }

    func urlSession(
        _ session: URLSession,
        didReceive challenge: URLAuthenticationChallenge,
        completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
    ) {
        evaluate(challenge, completionHandler: completionHandler)
    }

    func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        didReceive challenge: URLAuthenticationChallenge,
        completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
    ) {
        evaluate(challenge, completionHandler: completionHandler)
    }

    private func evaluate(
        _ challenge: URLAuthenticationChallenge,
        completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
    ) {
        guard
            challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
            let serverTrust = challenge.protectionSpace.serverTrust,
            challenge.protectionSpace.host == trustedHost
        else {
            completionHandler(.performDefaultHandling, nil)
            return
        }
        completionHandler(.useCredential, URLCredential(trust: serverTrust))
    }
}

/// Wraps a non-Sendable value so it can cross an actor boundary once.
/// Used to carry HealthKit's completion handler into the @MainActor task.
private final class UncheckedSendableBox<T>: @unchecked Sendable {
    let value: T
    init(_ value: T) { self.value = value }
}

struct HealthPayload: Codable, Sendable {
    let heartRate: Double?
    let glucose: Double?
    let weight: Double?
    let sleepHours: Double?
    let hrv: Double?
    let restingHeartRate: Double?
    let spo2: Double?
    let respiratoryRate: Double?
    let steps: Double?
    let timestamp: String

    init(
        heartRate: Double? = nil,
        glucose: Double? = nil,
        weight: Double? = nil,
        sleepHours: Double? = nil,
        hrv: Double? = nil,
        restingHeartRate: Double? = nil,
        spo2: Double? = nil,
        respiratoryRate: Double? = nil,
        steps: Double? = nil,
        timestamp: String
    ) {
        self.heartRate = heartRate
        self.glucose = glucose
        self.weight = weight
        self.sleepHours = sleepHours
        self.hrv = hrv
        self.restingHeartRate = restingHeartRate
        self.spo2 = spo2
        self.respiratoryRate = respiratoryRate
        self.steps = steps
        self.timestamp = timestamp
    }

    enum CodingKeys: String, CodingKey {
        case heartRate = "heart_rate"
        case glucose
        case weight
        case sleepHours = "sleep_hours"
        case hrv
        case restingHeartRate = "resting_heart_rate"
        case spo2
        case respiratoryRate = "respiratory_rate"
        case steps
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
    let hrv: Double?
    let restingHeartRate: Double?
    let spo2: Double?
    let respiratoryRate: Double?
    let steps: Double?
    let timestamp: String

    init(payload: HealthPayload) {
        heartRate = payload.heartRate
        glucose = payload.glucose
        weight = payload.weight
        sleepHours = payload.sleepHours
        hrv = payload.hrv
        restingHeartRate = payload.restingHeartRate
        spo2 = payload.spo2
        respiratoryRate = payload.respiratoryRate
        steps = payload.steps
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
