# qUnleashed Catalog

This is a public repository of community apps, menu styles and dolphin animations for Flipper Zero running Unleashed firmware.

This repository hosts manifests that contain metadata and build information. It doesn't host source code: every manifest points to a git repository where the code lives.

## How to install

Everything in this repository is built and archived by the qUnleashed catalog server. Use the [qUnleashed](https://github.com/DarkFlippers/qUnleashed) companion app to search and install apps, menu styles and animations.

## How to contribute

Read the [Contribution Guide](documentation/Contributing.md) to learn how to add and update your app, menu style or animation.

## How to report an issue

If you have found a bug in an app or want to suggest an improvement, please contact its developer using the contact information in the manifest, or open an issue in its source code repository.

If you want to report abuse or violation of your rights, please open an issue in this repo with details.

## Repository structure

- `applications` - app manifests, `applications/<Category>[/<Subcategory>]/<appid>/manifest.yml`
- `menustyles` - menu style manifests, `menustyles/<Category>/<appid>/manifest.yml`
- `animations` - dolphin animation manifests, `animations/<Pack>[/<Collection>]/<Name>/manifest.yml`
- `documentation` - catalog documentation, including the manifest format and the build process
- `example` - sample manifests for each kind of entry
- `tools` - CI/CD tools: verifying manifests and their code, creating code bundles, submitting them to the server

## Differences from the Flipper Apps Catalog

The format follows [flipper-application-catalog](https://github.com/flipperdevices/flipper-application-catalog), and an app manifest from there works here unchanged. On top of it:

- categories can be nested, `applications/GPIO/ESP32/<appid>`; the app is installed to the same path on the SD card, `/ext/apps/GPIO/ESP32/<appid>.fap`;
- menu styles and dolphin animations are catalogued next to apps;
- `commit_sha` may be left out for trusted repositories, such as [all-the-plugins](https://github.com/xMasterX/all-the-plugins) and friends of the project; such entries follow the repository HEAD and are rebuilt once a day;
- apps are built against the Unleashed firmware SDK.
