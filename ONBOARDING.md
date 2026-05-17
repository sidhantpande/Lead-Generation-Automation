# Onboarding & Credentials Setup Guide

Welcome to the **SimplifIQ Automated Lead Intelligence** workspace! This guide explains step-by-step how to acquire and configure all required credentials, keys, and tokens to run the pipeline successfully.

---

## 🔑 1. OpenAI API Key
Used for premium consulting copy synthesis and customized target prompt generation.

1. Navigate to the [OpenAI Developer Platform](https://platform.openai.com/).
2. Sign in or create a developer account.
3. Click on the **API Keys** tab on the left sidebar (under "Dashboard").
4. Click **Create new secret key**, name it `SimplifIQ-Enrichment`, and click **Create**.
5. Copy the secret key (`sk-proj-...`) immediately and paste it into your `.env` file under `OPENAI_API_KEY`.

---

## ♊ 2. Gemini API Key (Google AI Studio)
Used for the broad web search grounding sweep to map the prospect's digital footprint.

1. Navigate to [Google AI Studio](https://aistudio.google.com/).
2. Log in with your Google Workspace or Gmail account.
3. In the top-left corner, click the **Get API Key** button.
4. Click **Create API Key**, select an existing Google Cloud Project or create a new one, and hit **Create API Key in existing project**.
5. Copy your key (`AIzaSy...`) and paste it into your `.env` file under `GEMINI_API_KEY`.

---

## 📧 3. Gmail Address & Gmail App Password
Used for cost-free SMTP email dispatch with PDF attachments directly from your Gmail account.

### Step 3.1: Enable 2-Step Verification (Required)
1. Go to your [Google Account Settings](https://myaccount.google.com/).
2. Click **Security** on the left menu.
3. Under "How you sign in to Google", select **2-Step Verification** and complete the setup.

### Step 3.2: Generate the 16-Character App Password
1. In the **2-Step Verification** details page, scroll to the bottom and click on **App passwords** (or search "App passwords" in the top account search bar).
2. Enter a name for the app (e.g., `SimplifIQ Lead Gen`) and click **Create**.
3. A popup will reveal a **16-character code** (e.g., `byft slti bkaz xjxw`). Copy this code.
4. Paste your values into `.env`:
   - `GMAIL_ADDRESS=your_email@gmail.com`
   - `GMAIL_APP_PASSWORD=byft slti bkaz xjxw` *(you can include or exclude spaces; python will parse both!)*

---

## 🛠️ 4. Google Cloud Service Account (Drive & Sheets)
Allows the backend to securely upload PDFs and append row logs without prompting user consent screens.

### Step 4.1: Create a Service Account
1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Navigate to **APIs & Services** > **Library**. Search for and **Enable** two APIs:
   - **Google Drive API**
   - **Google Sheets API**
4. Navigate to **IAM & Admin** > **Service Accounts** on the left sidebar.
5. Click **Create Service Account** at the top.
6. Name it (e.g., `simplifiq-database`), click **Create and Continue**, skip optional role selection, and click **Done**.

### Step 4.2: Generate the JSON Credentials Key
1. Click on the newly created Service Account email from the list.
2. Go to the **Keys** tab at the top.
3. Click **Add Key** > **Create new key**.
4. Select **JSON** as the key type and click **Create**.
5. Save the downloaded JSON file into your project folder under:
   `credentials/service_account.json`

---

## 📁 5. Google Drive Folder ID
The folder where your PDF reports are stored and shared publicly.

1. Open [Google Drive](https://drive.google.com/).
2. Create a new folder (e.g., `SimplifIQ Reports`).
3. Double-click to enter the folder. Look at the URL in your browser:
   `https://drive.google.com/drive/folders/1koijIFFIeHq3H561mwP0eMJfsO_WHzvY`
4. Copy the alphanumeric string at the very end of the URL (e.g., `1koijIFFIeHq3H561mwP0eMJfsO_WHzvY`). This is your **GOOGLE_DRIVE_FOLDER_ID**.
5. Paste it into your `.env` file.
6. **CRITICAL**: Right-click the folder in Google Drive, select **Share**, and share it with your Google Service Account email address (found in your `service_account.json`) as **Editor**.

---

## 📊 6. Google Sheet ID
The tracking spreadsheet acting as your lead database.

1. Open [Google Sheets](https://sheets.google.com/) and create a new blank spreadsheet (e.g., `Lead Tracker`).
2. Add the following header titles in row 1:
   - Column A: `Date`
   - Column B: `Name`
   - Column C: `Email`
   - Column D: `Company`
   - Column E: `Website`
   - Column F: `Industry`
   - Column G: `Company Size`
   - Column H: `Drive Link`
   - Column I: `Status`
3. Look at your browser URL bar:
   `https://docs.google.com/spreadsheets/d/1bKDphgcKs8ZFbLihoostqWvhHWXKAJrKHVv1BxIRkJ8/edit`
4. Copy the long alphanumeric segment between `/d/` and `/edit` (e.g., `1bKDphgcKs8ZFbLihoostqWvhHWXKAJrKHVv1BxIRkJ8`). This is your **GOOGLE_SHEET_ID**.
5. Paste it into your `.env` file.
6. **CRITICAL**: Click **Share** in the top right, and add your Google Service Account email address (from `service_account.json`) as **Editor**.

---

## ✅ Verification
Once all values are set, verify everything immediately by running:
```bash
venv/bin/python3 scratch/test_pipeline.py
```
If you get `Success: All environment configurations are fully set!`, you are ready to boot up!
