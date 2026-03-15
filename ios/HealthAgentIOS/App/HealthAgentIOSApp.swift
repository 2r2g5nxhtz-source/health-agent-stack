import SwiftUI

@main
struct HealthAgentIOSApp: App {
    @StateObject private var viewModel = HealthAgentViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView(viewModel: viewModel)
        }
    }
}
