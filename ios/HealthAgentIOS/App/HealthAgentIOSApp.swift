import SwiftUI

@main
struct HealthAgentIOSApp: App {
    @StateObject private var viewModel = HealthAgentViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView(viewModel: viewModel)
                .task {
                    // Register HealthKit background delivery so new samples are
                    // posted automatically without a manual "Send Now" tap.
                    viewModel.startBackgroundDelivery()
                }
        }
    }
}
