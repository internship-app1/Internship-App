---
name: getting-started
description: run this skill when you are just getting started with internship matcher (i.e you just cloned the repo for the first time to contribute) This skill will help you from getting API keys, to starting the servers, to even making your first PR with both checks passing :)
---


## Step 0: Get your keys

Internship matcher has 2 .env files to use. One lives in the Frontend directory and the other lives at the root directory of the project.

Frontend/.env ==>

```
REACT_APP_ENVIRONMENT=development

# Usage tracking master switch (default: on). Baked in at build time.
# Set to "false" to remove the per-upload cooldown timer for dev testing.
# Must match the backend TRACK_USAGE value. Keep unset (or anything but "false")
# in production. A rebuild (npm run build) is required to change this.
REACT_APP_TRACK_USAGE=true

# Clerk Auth (get from https://dashboard.clerk.com → API Keys)
REACT_APP_CLERK_PUBLISHABLE_CLIENT_KEY=

# Backend URL (dev only — prod uses relative URLs via the proxy)
REACT_APP_API_URL=http://localhost:8000


```

Set the user up by doing the following:

For the frontend:
```
cp .env.example .env
```

Set the REACT_APP_ENVIRONMENT as development (it should ALMOST always be development)

Leave REACT_APP_TRACK_USAGE to true so we don't burn a BILLION dollars for our anthropic bill

for this key ==> REACT_APP_CLERK_PUBLISHABLE_CLIENT_KEY=

contact sujan at ``` nandikolsujan@gmail.com ```

for this REACT_APP_API_URL= 

usually we run the backend server at port 8000 but whatever port the user is running the backend on


# Setting up the backend

go to the root directory of the project and run

``` cp .env.example .env ```

after that , have the user fill in the keys.

The user should use their own keys for the following:
- claude key
- aws keys

For AWS keys, the user should already have it, so ask them to fill it in. if they're not sure ask them to be added as an IAM user to AWS by contacting ```nandikolsujan@gmail.com```

And the same goes for the supabase credentials

Make sure the users environment variable is always set to development , and track usage is set to true (unless testing a core feature in where the limits is a pain in the ass for testing) , skip setartup scrape should be set to 1 so it is less load on the server and good practice for scraping, so we aren't overloading other servers either.



The clerk key should already be given to the user if they successfully contacted me after the frontend/.env config.


## Step 1 -- Running the servers!


Before running the servers, INSTALL DEPENDENCIES!!!


frontend:
```cd frontend/ && npm i ```
if issues arise
```npm audit fix```
```npm i```

Now the frontend dependencies have been installed

Installing the backend dependencies:

from the root directory:

If Python 3.11 is already installed:
``` 
 python3.11 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
```
  If you need to install Python 3.11 first (via pyenv):
```
  # Install pyenv if needed
  brew install pyenv
  
  # Install Python 3.11
  pyenv install 3.11

  # Set it locally for this project
  pyenv local 3.11

  # Then create the venv
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
```
  Deactivate when done:
  deactivate

* 1 make sure virtual environment is configured, this project uses

There are 2 ways to run the servers. There is a bash script written that can be accessed by the root directory. You can run it by

``` ./start.sh --all ``` This runs the backend and frontend servers. However the issue with this script is that you can't monitor the backend logs by running this script.


So the other way is running them individually.

Run the frontend by: cd frontend && npm run dev
Run the backend from project root directory: uvicorn app:app --host 0.0.0.0 --port 8000 --reload


If any issues arise, fix them.

The most common issues:
- keys not set in .env . This could be either the frontend/.env or the root .env so prompt the user to make sure they set their keys
- one of the ports are already in use, this could happen for the frontend or the backend, so kill it using 
```
kill -9 $(lsof -t -i:<PORT_NUM>)
```
- Auth not working, if this happens this is likely because the user doesn't have their CLERK_PUBLISHABLE_KEY so prompt them to contact me at nandikolsujan@gmail.com


Now after all of that, the application should be running and working properly!!!


## Step 2 -- Self learn

Anytime you help out a user solve some issues that aren't noted in this file, always add a summary of the issue that happened, why it happens, and what the fix was. This way if any new user runs into the same issue, we have documentation of the issue + fix. Write them below and follow a format like

```
issue: a process running on port 8000
why it happens: the user has something else that is taking port 8000
the fix: use kill -9 $(lsof -t -i:8000) to free up that port and run the server again. Now the application works!
```

Write them in the Documentation of Issues and fixes section below:

## Documentation of Issues and Fixes



