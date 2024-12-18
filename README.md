
<h1>Linkedin GPT-based Posting Creator Assistant</h1>

I created this project because I wanted to create posts about cool articles and
papers that would come up every week, but did not have the time for it. So I decided
review them and post them.
to create a program that would generate the posts for me, and I would only need to

The program is based on the OpenAI's LLMs, through Langchain, but could be easily adapted to any other
LLM model. All design decisions are based on the idea that this program is meant to be run as a Windows service locally.
That's why all agents constantly update their status on a local file (so that if the laptop turns off abruptly, the status
is not lost). As of now, I still need to implement the behaviour for the stop signal though.


This program is comprised of 7 main components:
- Information Searching: This component is in charge of searching for information on the internet. It is based on the
  Google Search API, and it is implemented in the `searcher.py` file. It is a simple class that receives a query and
  returns a list of results. It is meant to be used by the `search_agent.py` agent.
- Telegram Bot: This component is in charge of communicating with the Telegram Bot API. It is implemented in the
  `telegram_bot.py` file. It is a simple class that receives a message and sends it to the Telegram Bot API. It is meant
  to be used by the `telegram_agent.py` agent.
- Linkedn Component: This component is in charge of generating the posts. It is implemented in the `posting.py` file. It
  is a simple class that receives a query and returns a list of results. It is meant to be used by the `posting_agent.py`
  agent.
- LLM Component: This component is in charge of generating the posts. It is implemented in the `llm.py` file. It is a
  simple class that receives a query and returns a list of results. It is meant to be used by the `llm_agent.py` agent.
- Windows Service: This component is in charge of running the program as a Windows service. It is implemented in the
  `service.py` file. It is a simple class that receives a query and returns a list of results. It is meant to be used by
  the `service_agent.py` agent.
- Main: This component is in charge of running the program. It is implemented in the `main.py` file. It is a simple class
  that receives a query and returns a list of results. It is meant to be used by the `main_agent.py` agent.

<h2>Installation</h2>

In order to install the program, you need to do the following:

- ### Install the dependencies

in conda:

```bash
  conda env create -f environment.yml
```

- ### Create a Telegram Bot and get the API key. 
  - Step 1. Open the Telegram app on your computer/phone
  To create a Telegram bot, you'll need to have the Telegram app installed on your computer. If you don't have it already, you can download it from the Telegram website.
  - Step 2. Connect to BotFather
    BotFather is a bot created by Telegram that allows you to create and manage your own bots. To connect to BotFather, search for "@BotFather" in the Telegram app and click on the result to start a conversation.
  - Step 3. Select the New Bot option
    In the conversation with BotFather, select the "New Bot" option to start creating your new bot. BotFather will guide you through the rest of the process.
  - Step 4. Add a bot name
  Next, BotFather will ask you to provide a name for your bot. Choose a name that accurately reflects the purpose of your bot and is easy to remember.
  - Step 5. Choose a username for your bot
  - Step 6. BotFather will ask you to choose a username for your bot. This username will be used to create a unique URL that people can use to access your bot. Choose a username that is easy to remember and related to your bot's purpose.

At the end of the process, you should have given a bot token by @botFather. You need to save that information, and other information such as the bot name that you chose on
the Telegram Bot config file on ./telegram/config.json:

```json
    
{
    "bot_name": "@whatever_bot_username",
    "name": "Your_Bot_Name(what appears on top)",
    "token": "Token given by BotFather"
}
    
```

- ### Configure Ngrok to have a persistant domain

  Create an account on Ngrok
    - Step 1. On https://dashboard.ngrok.com/get-started/setup/windows, copy the authtoken and paste
      it onto the the Telegram Bot config file. same as before, on ./telegram/config.json:
    - Step 2: Go to "Domains" on the left menu, and create a new domain.
    - Step 3: Copy the domain name and token that you generated and paste it into the Telegram Bot config file. same as before, on ./telegram/config.json:

        ```json
            
        {
          "ngrok_token": "Token given by Ngrok",
          "domain": "Domain given by Ngrok"
        }
            
        ```

Keep in mind that with the free version you can only have one domain.

- ### Configure you RapidAPI sources

  Create an account on RapidAPI: 
    - Step 1. Go to https://rapidapi.com/ and search for the following APIs:
        - Google Search API
    - Step 2. Subscribe to the Medium API:
    Go to https://rapidapi.com/nishujain199719-vgIfuFHZxVZ/api/medium2 and click on subscribe.
    - Step 3. Subscribe to the Google API:
    Go to https://rapidapi.com/rphrp1985/api/google-api31/ and click on subscribe.
    - Step 4. Copy the key that it shows after subscribing to the API on the API Key Header, ans paste into the config.json inside ./information/sources/rapid/news/config.json and ./information/sources/rapid/medium/config.json:

        ```json
            
        {
          "api_key": "Key given by RapidAPI"
        }
            
        ```

- ### Configure your Adobe PDF API

  Create an account on Adobe PDF
    - Step 1. Go to the Adobe Developer Console at https://developer.adobe.com/console/home 
    - Step 2. Click on "Create Project"
    - Step 2. Click on add API
    - Step 3. Select the "Adobe PDF Services API"
    - Step 4. Select OAuth Server to Server as the authentication method
    - Step 5. Check the Adobe PDF Services box
    - Step 6. Once created, you should see an OAuth API Key, and a button to generate an access token. Click on the credential. Now you should also 
  see an Organization ID at the bottom
    - Step 7. Click on generate access token, 
    - Step 9. Copy  OAuth API Key, Organization ID and the Access Token into the config.json inside ./pdf/config.json:

        ```json
            
        {
          "client_id": "OAuth API Key given by Adobe",
          "client_secret": "Access Token given by Adobe",
          "service_principal_credentials": {
            "organization_id": "Organization ID given by Adobe"
           }
        }
            
        ```

- ### Create you LinkedIn page and get the API key
  
  - Step 1. Go to Linkedin Developers: https://www.linkedin.com/developers/login and login with your Linkedin account.
  - Step 2. Go to "My Apps" and click on "Create App"
  - Step 3. Fill in all the information required, if you do not have a Linkedin page. You will need to do this as well.
  - Step 4: On you newly created app, go to Auth. 
  - Step 5: Copy your Client ID and Client Secret into the ./linkedin/config.json inside ./linkedin/config.json. You might need to click on generate first.

        ```json
            
        {
          "client_id": "Client ID given by Linkedin",
          "client_secret": "Client Secret given by Linkedin"
        }
            
        ```
  - Step 6: Check the OAuth 2.0 Scope permissions. For this project, you need to have these scope permissions (at least):
    - openid
    - email
    - w_member_social
    - profile
  
  - Step 7: Copy the persistant URL that we generated before with Ngrok, and paste it into the Authorized Redirect URLs section, adding /callback at the end:
    https://whatever_domain_you_generated/callback
  - Step 8. Go to the Products Tab, and request access for the following products:
    - Share on Linkedin
    - Sign In with LinkedIn using OpenID Connect
  After this, if you did not have the necessasry OAuth 2.0 Scope permissions, you should have them now.
  - Step 9. Go to the Team Members Tab, and make sure you appear as Team member. If you do not, add yourself as a team member.


- ### Configure your OpenAI API

    Create an account on OpenAI
    - Step 1. Go to https://beta.openai.com/ and login with your OpenAI account.
      - Step 2. Go to "My Account" and copy your API key.
        - Step 3. Paste your API key into the ./llm/langchain_agent/config.json file

          ```json
                
                   {
                    "environment": {
                      "OPENAI_API_KEY": "apikey"
                    }
                  }
                
          ```

      - Step 5. If instead of using the OpenAI API, you want to use the OpenAI, you are accessing OpenAI through service, like Azure, you also need to add some more information:
           ```json
                
               {
                "environment": {
                  "OPENAI_API_KEY": "apikey",
                  "OPENAI_API_TYPE": "type: for example azure",
                  "OPENAI_API_VERSION": "version: for example: 2023-09-15-preview",
                  "OPENAI_API_BASE": "your api base endpoint"
                }
        }
            
                
         ```
      - Step 6. Configure the OpenAI parameters. If using the OpenAI APIl only the model_name is necesssary. If using it from Open AI studio, you need to add the deployment_id as well.
      ```json
           {
              "openai_configs": {
                 "deployment_id": "",
                 "model_name": "gpt-4",
                 "max_tokens": 8192
               }
           }
       ```
      
- ### Install C++ Build Tools from Visual Studio

Torch requires C++ Build Tools from Visual Studio to be installed.

For this you can: 
1. Install Visual Studio (I installed 2022)
2. Install the C++ Desktop Development Workload
3. Open a command prompt and run: `where cl.exe` to find the path to the C++ compiler
4. Add the path to the C++ compiler to your PATH environment variable
5. Run `C:\Program Files\Microsoft Visual Studio xx.x\VC\vcvarsall.bat` (where xx.x is the version of Visual Studio you installed) to set up the environment variables for the C++ compiler

For my architecture and Windows SDK version (gets installed with the C++ Build Tools) I ran `\"Program Files"\"Microsoft Visual Studio"\2022\Enterprise\VC\Auxiliary\Build\vcvarsall.bat X64 10.0.22621.0`

- ### Install the Windows Service

  Activate the environment:

Open a CMD or Anaconda Prompt as Administrator, next steps will need to run on this session:

  If using conda: 

  ```bash
    conda activate linkedinassistant
   ```

Now, run the script `configurate.cmd` to configure the service.
This will create a data folder in `C:ProgramData/LinkedinAssistant` and copy the config files there.
You need to go back to the root folder of the project, and run the script:
```bash
  cd .. 
  configurate.cmd
 ```

When you run this program as a Windows Service, all logs and config files will be stored in `C:ProgramData/LinkedinAssistant` folder.

Then, you need to create the EXE file with pyinstaller:
Some popup error might appear, as long as it is related to torchvison or torchaudio, it is controlled and will be fine, just accept them and let it continue.    

```bash
pyinstaller --hidden-import win32timezone  --hidden-import torch --hidden-import torchvision --hidden-import torchaudio --collect-data torch --copy-metadata torch --collect-data torchvision --collect-data langchain --copy-metadata langchain --copy-metadata torchvision --collect-data torchaudio --copy-metadata torchaudio --copy-metadata packaging --copy-metadata safetensors --copy-metadata regex --copy-metadata huggingface-hub --copy-metadata tokenizers --copy-metadata filelock --copy-metadata datasets --copy-metadata numpy --copy-metadata tqdm --copy-metadata requests --copy-metadata pyyaml --clean --noconfirm src\windows\service.py
  ```

This will create the necessary EXE and dependencies in `dist` folder. 


After that: 


```bash
  .\dist\service\service.exe install
  ```

If this works, you have done everything correctly.


Optionally, you can set the service to start automatically when the computer starts:

```bash
  sc config linkedin_assistant start=delayed-auto
```


Finally, start the service:

```bash
 .\dist\service\service.exe start
```


<h2> Author </h2>
Daniel Cabrera Rodríguez

Github: @dan415

Email: danicr2515@gmail.com

Please, do not hesitate to contact if you have any questions or suggestions.


<h2> License </h2>

MIT License
Copyright (c) 2024 Daniel Cabrera Rodriguez

Permission is hereby granted, free of charge, to any person obtaining 
a copy of this software and associated documentation files (the "Software"), 
to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or 
sell copies of the Software, and to permit persons to whom the Software is 
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be 
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR 
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION 
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR 
THE USE OR OTHER DEALINGS IN THE SOFTWARE.



