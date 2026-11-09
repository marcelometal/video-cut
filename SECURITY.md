# Security Policy

## Reporting a Vulnerability

The Video Cut maintainers take security vulnerabilities seriously. If you
discover a security issue in Video Cut, please report it responsibly.

Please **DO NOT open a public GitHub issue** for security vulnerabilities.

Instead, please report the vulnerability privately using GitHub's
**Private Vulnerability Reporting** feature:

- Go to the repository's **Security** tab
- Click **Report a vulnerability**
- Submit the details through the GitHub Security Advisory form

Include as much information as possible to help us reproduce the issue:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- A proof of concept (PoC), if available
- Your environment: Video Cut version, how it was installed (Flatpak, AppImage,
  Debian package, Snap or from source), Linux distribution, and ffmpeg version

We will acknowledge receipt of your report as soon as possible and work with
you to understand and resolve the issue.

## Responsible Disclosure

We ask that you follow responsible disclosure practices:

- Do not publicly disclose the vulnerability before it has been addressed.
- Allow the maintainers reasonable time to investigate and fix the issue.
- Coordinate with us before publishing advisories, blog posts, or CVEs.

Once the issue is fixed, we will publicly acknowledge your contribution unless
you prefer to remain anonymous.

## Supported Versions

Security fixes are provided for the most recent release of Video Cut.

| Version        | Supported |
| -------------- | --------- |
| Latest release | ✅        |
| Older releases | ❌        |

Users are strongly encouraged to keep their Video Cut installation up to date.
Pre-built packages are published on the
[Releases page](https://github.com/thor27/video-cut/releases/latest).

## Security Considerations When Using Video Cut

Video Cut is a desktop application that reads and writes media through
`ffmpeg` and `ffprobe`. Please consider the following:

- Keep `ffmpeg`, `ffprobe`, GTK and GStreamer up to date, whether they come
  from your distribution or from a Flatpak runtime, since they do the actual
  decoding and encoding of your files.
- Treat video and image files from untrusted sources with the same care as any
  other downloaded file.
- Download Video Cut only from the official
  [Releases page](https://github.com/thor27/video-cut/releases) or from the
  package sources linked in the README.

## Acknowledgements

We appreciate the efforts of security researchers and the open-source community
in responsibly reporting vulnerabilities and helping improve the security of
Video Cut.
