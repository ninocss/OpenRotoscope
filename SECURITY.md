# Security Policy

OpenRoto processes local video frames, Resolve project context and model files, so security-sensitive reports should not be posted publicly before they are understood.

## Supported versions

OpenRoto is currently a pre-1.0 developer preview. Security fixes are made on the latest `main` branch and in the newest published release when releases are available.

## Reporting a vulnerability

Please use GitHub's private security-reporting feature for this repository when available.

Include:

- the affected OpenRoto commit or release;
- DaVinci Resolve edition/version when relevant;
- Windows version;
- a minimal reproduction;
- expected and observed behavior;
- whether the issue can expose local files, execute unintended code, bypass the loopback/session checks or modify the wrong Resolve timeline.

Do not include private footage, Resolve projects, credentials or model-service tokens unless they are strictly necessary to reproduce the issue.

If private security reporting is not enabled yet, contact the repository owner privately rather than opening a public issue with exploit details.

## Scope notes

OpenRoto deliberately limits Resolve bridge communication to local mechanisms: authenticated loopback IPC for the Studio bridge and filesystem-local handoff for Resolve Free. Optional third-party removal backends execute in separate local Python environments and are outside OpenRoto's redistribution boundary.
