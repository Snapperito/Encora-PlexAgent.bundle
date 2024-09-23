![Encora Reprise](Contents/Resources/icon-default.png)

# Encora Plex Agent

This agent will scrape recording data from Encora, including downloading subtitles.
It will also fallback to using [XBMCnfoMoviesImporter](https://github.com/Bubba8291/XBMCnfoMoviesImporter.bundle/archive/master.zip) if no encora ID is found, so that NFO files (created with [NFOBuilder](https://github.com/pekempy/NFOBuilder)) can be used to set the data.

<sup>Thanks to [Bubba8291](https://github.com/Bubba8291) for working on the Headshot Database used for the agent.</sup>

_Please note: The Encora API is rate limited to 30 requests per minute by default. This means that scanning your full library make take time if you have a large amount of recordings in Plex.
The agent is configured to handle the rate limit and continue processing entries once the limit resets._

### Instructions

- Download the entire repository ([click here](https://github.com/pekempy/Encora-PlexAgent.bundle/archive/refs/heads/main.zip)) and extract the folder inside
- Rename `Encora-PlexAgent.bundle-main` -> `Encora-PlexAgent.bundle`
- Move the .bundle folder to your Plugins Directory
  - By default, this will be:
    - Windows: `%LOCALAPPDATA%\Plex Media Server\Plug-ins`
    - macOS: `~/Library/Application Support/Plex Media Server/Plug-ins`
    - Linux: `$PLEX_HOME/Library/Application Support/Plex Media Server/Plug-ins`
  - It should look like this:  
    ![Plugin Preview](src/plugins-folder.png)
- Create a library in Plex with `Encora` as the agent
- Populate your API Key in the settings
- Configure the naming of Plex items
  ![Plex Library](src/plex-library.png)
- In your Plex Settings, make sure you enable XBMCnfoMoviesImporter as a backup agent for Encora
  ![Agent Setting](src/plex-agent.png)
- Your media items should have `e-{id}` in the name e.g. `Murder Ballad {e-1118317}` **or** have an `.encora-{id}` file inside the folder e.g. `.encora-1118317`
