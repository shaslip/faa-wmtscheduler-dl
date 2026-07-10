# FAA WMT Scheduler Downloader

An automated script using Playwright to log into the FAA WMT Scheduler, navigate Okta authentication, and download the current and next pay period schedules to a JSON file.

## Prerequisites
- Python 3.8+
- Linux/macOS/Windows

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/shaslip/faa-wmtscheduler-dl.git
   cd faa-wmtscheduler-dl
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

4. **Configuration:**
   Create a `.env` file in the root directory and add your credentials:
   ```env
   FAA_EMAIL="your.email@faa.gov"
   FAA_PASSWORD="YourPasswordHere"
   FAA_INITIALS="XX"
   ```

## Usage

**Run manually:**
```bash
python3 scheduler.py
```

**Automate with Cron (Linux):**
To run automatically every Monday at 8:00 AM in the background, add this to your crontab (`crontab -e`):
```bash
0 8 * * 1 cd /path/to/faa-wmtscheduler-dl && /usr/bin/python3 scheduler.py >> scheduler_cron.log 2>&1
```
