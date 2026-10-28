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

- `applications` - app manifests, `applications/<Category>[/<Subcategory>]/<appid>/manifest.yml`; once a day app-stream adds those of the official catalog we have none of, in the top folder of their category, and updates our unchanged copies of its manifests
- `menustyles` - menu style manifests, `menustyles/<Category>/<appid>/manifest.yml`
- `animations` - dolphin animation manifests, `animations/<Pack>[/<Collection>]/<Name>/manifest.yml`
- `servers.yml` - the domains of the catalog servers, publish sends every bundle to each of them
- `trusted.yml` - repositories app-stream pins to their latest commit; their apps may need the whole firmware tree to build
- `documentation` - catalog documentation, including the manifest format and the build process
- `example` - sample manifests for each kind of entry
- `tools` - CI/CD tools: checking manifests and their code, assembling bundles, publishing them to the server

Next to every published manifest the CI keeps the entry's bundle as the server received it: `bundle/` and `bundle.json`.

## Differences from the Flipper Apps Catalog

The format follows [flipper-application-catalog](https://github.com/flipperdevices/flipper-application-catalog), and an app manifest from there works here unchanged. On top of it:

- categories can be nested, `applications/GPIO/ESP32/<appid>`; the app is installed to the same path on the SD card, `/ext/apps/GPIO/ESP32/<appid>.fap`;
- menu styles and dolphin animations are catalogued next to apps;
- `commit_sha` may be left out for repositories in `trusted.yml`, such as [all-the-plugins](https://github.com/xMasterX/all-the-plugins); app-stream writes it in once a day, the last commit that changed the app;
- apps are built against the Unleashed firmware SDK.
