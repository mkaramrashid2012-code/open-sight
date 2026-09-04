# 🎥 OpenSight Private - Local Video Analytics Platform

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Open Source](https://img.shields.io/badge/open-source-green.svg)](https://github.com/mkaramrashid2012-code/open-sight)
[![Privacy First](https://img.shields.io/badge/privacy-100%25_local-orange)](#-privacy-by-design)

> **Enterprise-grade video analytics platform that runs 100% locally on your machine.**
> 
> Detect objects, track movements, search video events, and manage surveillance—all without sending data to the cloud. Privacy-first, open-source, and self-hosted.

---

## 🌟 Key Features

✅ **100% Local & Private** - Process video streams without cloud dependencies  
✅ **Object Detection** - YOLOv8-powered detection for people, vehicles, and more  
✅ **Multi-Object Tracking** - Track and follow objects across video frames  
✅ **Video Search** - Find events, objects, and behaviors using intelligent queries  
✅ **Self-Hosted** - Complete control over your data and infrastructure  
✅ **Easy to Run** - Works on Windows, macOS, and Linux  
✅ **Professional Architecture** - Production-ready foundation with modular design  
✅ **Privacy Controls** - Face recognition & sensitive features disabled by default  

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Windows/macOS/Linux**
- **2GB RAM minimum** (4GB recommended)
- **Docker (optional)** for database

### Installation (2 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/mkaramrashid2012-code/open-sight.git
cd open-sight

# 2. Create virtual environment
python -m venv .venv

# 3. Activate it
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the demo
python run_demo.py
```

That's it! The demo will:
- Create sample tracking data
- Smooth trajectories  
- Calculate quality scores
- Generate searchable events
- Export evidence packages

---

## 📁 What's Inside

```
open-sight/
├── backend/                    # Main application code
│   ├── tracking/              # Object tracking engine
│   ├── search/                # Intelligent search system
│   ├── security/              # Audit logging
│   ├── cases/                 # Case management
│   ├── retention/             # Data retention policies
│   └── evidence/              # Evidence export
├── database/                  # PostgreSQL schema
├── tests/                     # Unit tests
├── run_demo.py               # Demo runner
└── requirements.txt          # Python dependencies
```

---

## 💡 Use Cases

- **Personal Security** - Monitor your property locally
- **Investigation** - Search and export evidence
- **Privacy-Preserving Monitoring** - Keep data on your machine
- **Research & Development** - Test video analytics locally
- **Forensic Analysis** - Case management and evidence tracking

---

## 🔒 Privacy & Security

### Zero Cloud Dependency
- ✅ All processing happens on your machine
- ✅ No video streams sent to external servers
- ✅ No telemetry or tracking
- ✅ Complete offline capability

### Privacy Defaults
- 🛡️ Face recognition **disabled** by default
- 🛡️ License plate recognition **disabled** by default
- 🛡️ Full audit logging of all operations
- 🛡️ GDPR/HIPAA aligned design

---

## 🛠️ Technical Stack

| Component | Technology | Status |
|-----------|-----------|--------|
| **Detection** | YOLOv8 | ✅ Ready |
| **Tracking** | State Machine + Trajectory | ✅ Ready |
| **Search** | Explainable Query Model | ✅ Ready |
| **Database** | PostgreSQL + pgvector | ✅ Ready |
| **Export** | Evidence Packaging | ✅ Ready |
| **Testing** | pytest | ✅ Ready |

---

## 📊 Roadmap

### Phase 1 ✅ (Current)
- [x] Professional tracking architecture
- [x] Trajectory smoothing
- [x] Quality scoring
- [x] Explainable search
- [x] Evidence export
- [x] Unit tests

### Phase 2 🔜 (Coming Soon)
- [ ] Camera ingestion (RTSP)
- [ ] Real-time object detection
- [ ] Dashboard UI
- [ ] Search API
- [ ] Video recording

### Phase 3 📅 (Future)
- [ ] Multi-camera tracking
- [ ] Advanced analytics (zones, line crossing)
- [ ] Appearance re-identification
- [ ] Mobile app

---

## 🧪 Testing

Run the test suite:

```bash
pytest
```

Expected output:
```
3 passed
```

---

## 📖 Documentation

- **[Project Structure](README.md#-project-structure)** - How it's organized
- **[Requirements](README.md#-minimum-requirements)** - Hardware & software needs
- **[Setup Guide](README.md#-how-to-build-and-run-locally)** - Step-by-step installation
- **[API Overview](docs/API.md)** - REST endpoints (coming soon)
- **[Troubleshooting](README.md#-troubleshooting)** - Common issues & fixes

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

```bash
# Fork the repo → Clone → Create a branch → Make changes → Submit PR
git checkout -b feature/my-feature
git commit -m "Add my feature"
git push origin feature/my-feature
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## ❓ FAQ

**Q: Will my video be stored?**  
A: Only if you enable recording. By default, only detection events and metadata are stored locally.

**Q: Is this production-ready?**  
A: The skeleton is production-ready for video analytics logic. Camera integration is coming soon.

**Q: Can I use this for commercial purposes?**  
A: Only under AGPL-3.0 (open-source sharing required). Contact us for commercial licenses.

**Q: How do I enable face recognition?**  
A: You can't (by design). It's intentionally disabled for privacy. Use at your own risk with legal compliance.

---

## 📞 Support & Community

- 💬 **Discussions** - Ask questions in [GitHub Discussions](../../discussions)
- 🐛 **Issues** - Report bugs in [GitHub Issues](../../issues)
- 📧 **Email** - Contact: mkaramrashid2012@gmail.com

---

## 📄 License

**GNU Affero General Public License v3.0 (AGPL-3.0)**

This means:
- ✅ Free to use, modify, and distribute
- ✅ Must share source code if deployed
- ✅ Must include license notice

See [LICENSE](LICENSE) file for details.

---

## ⚖️ Disclaimer

OpenSight Private is designed for **authorized and lawful surveillance only**. Users are responsible for:
- Complying with local privacy and surveillance laws
- Obtaining proper consent from monitored individuals
- Using this tool ethically and legally
- Maintaining audit logs for accountability

**This is NOT meant for:**
- Covert surveillance
- Unauthorized monitoring
- Privacy violations
- Illegal activities

---

## 🙏 Acknowledgments

Built with modern open-source tools:
- [Python](https://www.python.org/)
- [PostgreSQL](https://www.postgresql.org/)
- [pytest](https://pytest.org/)
- [Docker](https://www.docker.com/)

---

**Made with ❤️ for privacy and local control.**

**Latest Version:** 1.0.0  
**Last Updated:** 2026

---

*Star this repo if you find it useful! ⭐*
