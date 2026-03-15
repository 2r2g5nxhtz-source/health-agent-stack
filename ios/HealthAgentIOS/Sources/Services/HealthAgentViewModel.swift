import Foundation
import HealthKit

@MainActor
final class HealthAgentViewModel: ObservableObject {
    @Published var statusMessage = "Ready"
    @Published var isLoading = false
    @Published var lastPayload: HealthPayload?
    @Published var lastWarnings: [String] = []
    @Published var webhookURLString: String

    private let healthStore = HKHealthStore()
    private let webhookKey = "healthAgent.webhookURL"
    private let defaultWebhookURL = "http://192.168.1.105:5678/webhook/apple-health"

    init() {
        webhookURLString = UserDefaults.standard.string(forKey: webhookKey) ?? defaultWebhookURL
    }

    func saveWebhookURL() {
        let trimmed = webhookURLString.trimmingCharacters(in: .whitespacesAndNewlines)
        webhookURLString = trimmed.isEmpty ? defaultWebhookURL : trimmed
        UserDefaults.standard.set(webhookURLString, forKey: webhookKey)
    }

    func requestPermissionsAndSend() async {
        guard HKHealthStore.isHealthDataAvailable() else {
            statusMessage = "Health data is not available on this device."
            return
        }

        guard let webhookURL = URL(string: webhookURLString), let scheme = webhookURL.scheme, ["http", "https"].contains(scheme) else {
            statusMessage = "Webhook URL is invalid."
            return
        }

        isLoading = true
        lastWarnings = []
        statusMessage = "Requesting Health access..."

        do {
            saveWebhookURL()
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
        } catch {
            statusMessage = error.localizedDescription
        }

        isLoading = false
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
        request.httpBody = try JSONEncoder().encode(payload)

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw HealthAgentError.invalidResponse
        }
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
