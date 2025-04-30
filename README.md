# 🏠 Apartments.com Scraper

This is a personal project that I built while apartment hunting. Here are some of its features:

- Scrapes listings for studio, 1-bedroom, and 2-bedroom apartments in city of choice
- Filters listings by price with different price ranges for each layout
- Extracts:
  - Link
  - Location
  - Price
  - Size
  - In-unit laundry (TRUE/FALSE)
  - Contact phone (if available)
- Sorts listings by minimum price
- Outputs directly to Google Sheets for easy record management

In the end, you only see listings with your selected amenities, without having to manually go through each listing's webpage.

## 🧰 Technologies Used

- Python
- [Selenium](https://pypi.org/project/selenium/) — browser automation
- [BeautifulSoup4](https://pypi.org/project/beautifulsoup4/) — HTML parsing
- [gspread](https://pypi.org/project/gspread/) — Google Sheets API client
- [oauth2client](https://pypi.org/project/oauth2client/) — auth for Google APIs
- Google Chrome + ChromeDriver


## ⚙️ Setup Instructions

### 1. Clone this Repo

```bash
git clone https://github.com/yourusername/apartments-scraper.git
cd apartments-scraper
```

### 2. Install Dependencies

```bash
pip install selenium beautifulsoup4 gspread oauth2client
```

### 3. Set Up Google Cloud Credentials

#### a. Create a Google Cloud Project

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g. `apartments-scraper`)

#### b. Enable APIs

Go to **APIs & Services > Library** and enable:

- Google Sheets API
- Google Drive API

#### c. Create a Service Account

1. Go to **APIs & Services > Credentials**
2. Click **"Create Credentials" → Service account**
3. Name it something like `sheets-writer`
4. Skip permissions
5. Click **"Create Key" → JSON**
6. Save the `.json` file to your project directory, e.g., `google-creds.json`

> ⚠️ Share your Google Sheet with the service account email (found in the JSON file under `client_email`)


## 📄 Usage

### 1. Create a Google Sheet

- Make a blank sheet with any title
- Copy the **spreadsheet ID** from the URL  
  (it’s the long string between `/d/` and `/edit`)

### 2. Run the Scraper

```bash
python apartments_scraper.py path/to/google-creds.json YOUR_SPREADSHEET_ID
```


## 📌 Output

Your Google Sheet will be filled with:

| Link | Location | Price | Size | In-unit laundry (T/F) | Contact |
|------|----------|-------|------|------------------------|---------|




## 📜 License

MIT License. Use responsibly and respect [Apartments.com's terms](https://www.apartments.com/legal/terms/).