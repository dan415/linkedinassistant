# LinkedIn Gen AI Driven Posting Creator Assistant

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.10578028.svg)](https://doi.org/10.5281/zenodo.10578028)
[![readthedocs](https://readthedocs.org/projects/linkedinassistant/badge/?version=latest)](https://linkedinassistant.readthedocs.io/en/latest/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

This project was created to simplify the process of sharing posts about fascinating articles and papers that surface every week. The program generates drafts for these posts, allowing the user to focus only on reviewing and publishing.


write the md to import an image

![LinkedIn Assistant](./docs/linkedin_assistant.svg)

## Components Overview

This program comprises the following components:
- **Core**: Implements shared utilities like configuration management and Vault secrets handling.
- **Information**: Handles raw information scraping and generates initial publication drafts.
- **Telegram**: Acts as the user interface via a Telegram bot.
- **LinkedIn**: Manages LinkedIn API interactions and OAuth server functionalities.

---

## Installation

---

### Step 1: Set Up HashiCorp Secrets Vault

#### Step 1: Set Up HCP Account
1. **Sign Up/Login**: Visit the [HashiCorp Cloud Platform](https://cloud.hashicorp.com/) and log in or create an account.
2. **Billing**: Add billing details.


#### Step 2: Create an HCP Organization
1. Navigate to **Organizations** and create one.
2. Save the **Organization Name** as `HCP_ORGANIZATION`.


#### Step 3: Create an HCP Project
1. In your organization, navigate to **Projects** and create one.
2. Save the **Project Name** as `HCP_PROJECT`.


#### Step 4: Set Up HCP Vault
1. Go to **HashiCorp Vault** and create a Vault cluster.
2. Save the cluster details.


#### Step 5: Create an Application in HCP Vault
1. Go to **Access Control** and create an application. Save the **App Name** as `HCP_APP`.
2. Generate a **Client ID** and **Client Secret**, saving them as `HCP_CLIENT_ID` and `HCP_CLIENT_SECRET`.


#### Environment Variables
Create a `.env` file at the root project level:
```
HCP_ORGANIZATION=your_organization
HCP_PROJECT=your_project
HCP_APP=your_app
HCP_CLIENT_ID=your_client_id
HCP_CLIENT_SECRET=your_client_secret
```

*Note: This environment variables will only be needed up until installation is completed. After that, they will have 
been loaded into the system's keyring or into Dockerized environment*

---

### Step 2: Set Up MongoDB Atlas

#### Step 1: Create a MongoDB Atlas Account
1. Visit [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) and sign up.
2. Deploy a free M0 Sandbox cluster.
3. Obtain the connection string and save it as `MONGO_URI`.

All necessary collections and documents will be created at start time. Necessary configs reside inside 
*res/json/default_configs.json*.

---

### Step 3: Set Up Backblaze B2 File Storage

1. Sign up at [Backblaze](https://www.backblaze.com/).
2. Create a B2 Cloud Storage bucket named `linkedin-assistant`.
3. Generate application keys and save them as `BLACBLAZE_API_KEY` and `BLACBLAZE_KEY_ID`.

---

### Step 4: Set Up Telegram Bot

1. Connect to [BotFather](https://t.me/BotFather).
2. Create a bot and save the token as `TELEGRAM_BOT_TOKEN`.
3. Store the bot configuration in MongoDB:


```json
{
  "bot_name": "@your_bot_username",
  "name": "Your Bot Name",
  "token": "your_bot_token"
}
```

---

### Step 5: Configure LinkedIn API

  - Step 1: Go to Linkedin Developers: https://www.linkedin.com/developers/login and login with your Linkedin account.
  - Step 2. Go to "My Apps" and click on "Create App"
  - Step 3. Fill in all the information required, if you do not have a Linkedin page. You will need to do this as well.
  - Step 4: On you newly created app, go to Auth. 
  - Step 5: Save these in your Vault as `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET`.
  - Check the OAuth 2.0 Scope permissions. For this project, you need to have these scope permissions (at least):
    - openid
    - email
    - w_member_social
    - profile
  - Step 6: Copy the persistant URL that we generated before with Ngrok without the HTTP schema and set it in your vault as `NGROK_DOMAIN`
  - Step 8. Go to the Products Tab, and request access for the following products:
    - Share on Linkedin
    - Sign In with LinkedIn using OpenID Connect
    
  After this, if you did not have the necessasry OAuth 2.0 Scope permissions, you should have them now.
  - Step 9. Go to the Team Members Tab, and make sure you appear as Team member. If you do not, add yourself as a team member.

---

### Step 6: Set Up Rapid API (Optional, if want to use Rapid API sources)

  Create an account on RapidAPI: 
    - Step 1. Go to https://rapidapi.com/ and search for the following APIs:
        - Google Search API
    - Step 2. Subscribe to the Medium API:
    Go to https://rapidapi.com/nishujain199719-vgIfuFHZxVZ/api/medium2 and click on subscribe.
    - Step 3. Subscribe to the Google API:
    Go to https://rapidapi.com/rphrp1985/api/google-api31/ and click on subscribe.
    - Step 4: Subscribe to Youtube Transcribe API: 
      Go to https://rapidapi.com/ and click subscribe
    - Step 5. Copy the key that it shows after subscribing to the API on the API Key Header, and set it in you vault 
      as `RAPID_API_KEY`

---
  
### Step 8: Obtain Youtube API Key from Google Cloud Platform (Optional, if want to use Youtube as source)


#### Step 1: Set Up a Google Cloud Project
- Log in to Google Cloud Console
- Go to Google Cloud Console.

- Create a New Project

- Click on the "Select a project" dropdown in the top navigation bar.
- Click New Project.
- Enter a Project Name, choose your Billing Account (if prompted), and click Create.

#### Step 2: Enable YouTube Data API v3
- Navigate to the APIs & Services Dashboard
- In the left-hand menu, click APIs & Services > Library.
- Search for YouTube Data API v3

- In the search bar, type YouTube Data API v3.
- Click on the API from the search results.
- Enable the API

- Click the Enable button to activate the YouTube Data API for your project.

#### Step 3: Create API Credentials
- Go to the Credentials Page
- In the left-hand menu, click APIs & Services > Credentials.
- Click "Create Credentials"
- In the top toolbar, click the "Create Credentials" button.
- Select API Key from the dropdown.
- Copy the API Key

- After creation, a pop-up will display your new API key.
- Click the Copy icon and save the key somewhere secure.

#### Step 4: Restrict Your API Key (Optional)

- To ensure security, restrict how and where your API key can be used:
- Edit API Key Restrictions
- On the Credentials page, click the Edit icon next to your API key.
- Set Application Restrictions
- Under Application restrictions, select HTTP referrers (web sites).
- Add the URL of your website or application.
- Set API Restrictions
- Under API restrictions, select Restrict key.
- Select the YouTube Data API v3 from the dropdown.
- Click Save.

---

### Step 9: Set up desired LLM providers

Available supported providers are:

- OpenAI
- Groq
- Google Gen AI
- Deepseek

You can obtain the API keys for these providers and set them in your Vault as `OPENAI_API_KEY`,
`GROQ_API_KEY`, `GOOGLE_GEN_AI_API_KEY`, and `DEEPSEEK_API_KEY` respectively.

**Note: OpenAI is the only image model provider available at the moment. Therefore, it is mandatory to set the `OPENAI_API_KEY` in your Vault,
if you want to use the image generation tool**.

---

### Step 10: Install C++ Build Tools from Visual Studio (Only if installing as Windows Service)

Torch requires C++ Build Tools from Visual Studio to be installed.

For this you can: 
1. Install Visual Studio (I installed 2022)
2. Install the C++ Desktop Development Workload
3. Open a command prompt and run: `where cl.exe` to find the path to the C++ compiler
4. Add the path to the C++ compiler to your PATH environment variable
5. Run `C:\Program Files\Microsoft Visual Studio xx.x\VC\vcvarsall.bat` (where xx.x is the version of Visual Studio you installed) to set up the environment variables for the C++ compiler

For my architecture and Windows SDK version (gets installed with the C++ Build Tools) I ran `\"Program Files"\"Microsoft Visual Studio"\2022\Enterprise\VC\Auxiliary\Build\vcvarsall.bat X64 10.0.22621.0`


--- 

### Step 11: Install the service

If using Windows:

---

1. Open root project folder on CMD Terminal with Admin Privileges and run
2. Run .\install.bat  (If you want to rebuild the EXE file run with argument --rebuild)

The program will ask for your user password in order to install the service with your account (It will not validate
it but installation will fail at the end if incorrectly provided)

---


If using Unix, on terminal, run:

```bash
sudo ./install.sh
```

---


## Author
**Daniel Cabrera Rodríguez**

- **GitHub**: [@dan415](https://github.com/dan415)
- **Email**: danicr2515@gmail.com

Feel free to reach out with questions or suggestions!

---

## License

MIT License © 2024 Daniel Cabrera Rodríguez

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

