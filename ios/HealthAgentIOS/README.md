# HealthAgentIOS

Минимальное iPhone-приложение для отправки последних данных Apple Health в `n8n`.

## Что делает

- читает последние `heart_rate`, `glucose`, `weight`
- суммирует `sleep_hours` за последние 24 часа
- отправляет JSON на настраиваемый webhook `n8n`
- может отправлять заголовок `X-Health-Agent-Secret` для защищённого webhook

## Payload

```json
{
  "heart_rate": 79,
  "glucose": 112,
  "weight": 81.9,
  "sleep_hours": 5.5,
  "timestamp": "2026-03-15T08:00:00Z"
}
```

## Как открыть в Xcode

1. Установить `xcodegen`, если его нет.
2. В папке `ios/HealthAgentIOS` выполнить `xcodegen generate`.
3. Открыть `HealthAgentIOS.xcodeproj`.
4. В `Signing & Capabilities` выбрать свою команду (`Team`).
5. Подключить iPhone и запустить на устройстве.

## Как собрать `.ipa`

1. Открой `HealthAgentIOS.xcodeproj` и один раз выбери свой `Team` в `Signing & Capabilities`.
2. Узнай свой `Team ID` в Xcode и замени `REPLACE_WITH_YOUR_TEAM_ID` в одном из файлов:
   - `export/ExportOptions.ad-hoc.plist`
   - `export/ExportOptions.app-store.plist`
3. Для установки на свои устройства используй `ad-hoc`:

```bash
cd ios/HealthAgentIOS
chmod +x scripts/export-ipa.sh
./scripts/export-ipa.sh
```

4. Готовый архив будет в:

```text
ios/HealthAgentIOS/build/export
```

5. Если нужен экспорт для App Store Connect, запусти так:

```bash
cd ios/HealthAgentIOS
EXPORT_OPTIONS_PLIST="$PWD/export/ExportOptions.app-store.plist" ./scripts/export-ipa.sh
```

## Что важно про `.ipa`

- Без корректного `Signing` и профиля `.ipa` не экспортируется.
- Для простой установки на свой iPhone чаще всего удобнее сначала нажать `Run` из Xcode, а уже потом пользоваться `export-ipa.sh`.
- `ad-hoc` подходит для ручной установки на зарегистрированные устройства.
- `app-store-connect` подходит для загрузки в App Store Connect и TestFlight.

## Что нужно проверить

- iPhone и Mac в одной сети с `n8n`
- у приложения есть доступ к Health
- webhook `n8n` активен
- в приложении введён ваш собственный webhook URL
- если используется secure workflow, в приложении указан тот же shared secret
