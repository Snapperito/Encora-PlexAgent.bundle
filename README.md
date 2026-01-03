![Encora Reprise](Contents/Resources/icon-default.png)

# Encora Plex Agent

This agent will scrape recording data from Encora, including downloading subtitles.
It will also fallback to using [XBMCnfoMoviesImporter](https://github.com/gboudreau/XBMCnfoMoviesImporter.bundle/archive/refs/heads/master.zip) if no encora ID is found, so that NFO files (created with [NFOBuilder](https://github.com/pekempy/NFOBuilder)) can be used to set the data.

<sup>Thanks to [Bubba8291](https://github.com/Bubba8291) for working on the [Headshot Database](https://stagemedia.me) used for the agent.</sup>

_Please note: The Encora API is rate limited to 30 requests per minute by default. This means that scanning your full library make take time if you have a large amount of recordings in Plex.
The agent is configured to handle the rate limit and continue processing entries once the limit resets._
You will also require an API key for [StageMedia.me](https://stagemedia.me) so make sure to generate one over there, or you won't get headshots/posters pulled through.

---

### Contents

- [Install instructions](#instructions)
- [Available title variables](#available-title-variables)
- [Fixing missing posters/headshots](#fixing-missing-posters--headshots)

---

### Instructions

- Download the entire repository ([click here](https://github.com/pekempy/Encora-PlexAgent.bundle/archive/refs/heads/main.zip)) and extract the folder inside
- Rename `Encora-PlexAgent.bundle-main` -> `Encora-PlexAgent.bundle`
- Move the `.bundle` folder to your Plugins Directory
  - By default, this will be:
    - Windows: `%LOCALAPPDATA%\Plex Media Server\Plug-ins`
    - macOS: `~/Library/Application Support/Plex Media Server/Plug-ins`
    - Linux: `$PLEX_HOME/Library/Application Support/Plex Media Server/Plug-ins`
  - It should look like this:  
    ![Plugin Preview](src/plugins-folder.png)
- Create a library in Plex with `Encora` as the agent
- Populate your API Keys in the settings
  - Note:
    The **Encora** API key you will have to request via a support request on the site.  
     The **StageMedia** API key is self-generated from your profile
- Configure the naming of Plex items
  ![Plex Library](src/plex-library.png)
- In your Plex Settings, make sure you enable XBMCnfoMoviesImporter as a backup agent for Encora
  ![Agent Setting](src/plex-agent.png)
- Your media items should have `e-{id}` in the name e.g. `Murder Ballad {e-1118317}` **or** have an `.encora-{id}` file inside the folder e.g. `.encora-1118317`
- For non-Encora items, make sure you have an NFO created with [NFOBuilder](https://github.com/pekempy/NFOBuilder), and then `⋮` button -> `Match` -> `Auto Match` dropdown -> `XBMCnfoMoviesImporter`, that should then detect the NFO and pull the data from it.

---

#### Available Title Variables:

**Text:**
`{show}` - This is the show's name - e.g. `Hadestown`. Note, if a show has "Part 1" and "Part 2", these should be removed.  
`{tour}` - The name of the tour - e.g. `West End` or `Broadway`  
`{master}` - The name of who recorded the item

**Dates:**
`{date}` - e.g. `December 31, 2024`  
`{date_iso}` - e.g. `2024-12-31`  
`{date_usa}` - e.g. `12-31-2024`  
`{date_numeric}` - e.g. `31-12-2024`  
If the entry has a 'variant' it will be displayed as `(1)` at the end of the value e.g. `December 31, 2024 (3)`

If a show is missing a month / day, the `date replace character` in the library preferences can be set so for example you can have `xx-xx-2024` or `12-xx-2024` or even `2024-12-##` - any standard character can be used. Only the first one will be used so if you enter multiple letters here just the first gets used.

---

### Fixing missing posters / headshots

If posters or headshots are missing from your Plex after matching on Encora, then you will need to contribute to the [StageMedia.me database](https://stagemedia.me).
You can upload images there, and then press the `⋮` button, and `Refresh Metadata` in Plex, and you should now have headshots for those actors/posters for that show in your Plex.  
NB: if `Refresh Metadata` does not work, you may need to re-match, or fix the match manually.

This helps _everyone_ who uses this plugin, not just you!

You will need your own account for this site, so sign up and contribute what you can :)

---

### Additional "flair"

If you want to add an `Edition` to your Plex items automatically, I found a way using [N8N](https://n8n.io/) which I self-host.
The purpose of `Edition` shows the "master" (pulled from Director on plex) underneath the show name, next to the year.

The workflow I use is as follows:

1. Schedule Trigger -> Daily    
2. Query -> PlexAPI for Theatre Library Items    
    HTTP Request    
    GET `http://{local plex IP}:32400/library/sections/{theatre library ID}/all`    
        where {theatre library ID} is the ID of your theatre library in Plex, e.g. `3`    
    Auth Type:    
        Generic Credential > Header Auth    
        Header: `X-Plex-Token`: {your Plex token}    
3. `Code` node with this JS:
```js
const items = [];

const videos = $json.MediaContainer?.Metadata || [];

for (const v of videos) {
  const directorTags = (v.Director || []).map(d => d.tag);

  const newEditionTitle = directorTags.length
    ? directorTags.join(" / ")
    : null;

  items.push({
    ratingKey: v.ratingKey,
    title: v.title,
    editionTitle: v.editionTitle || null,
    newEditionTitle,
    mediaPath: v.Media?.[0]?.Part?.[0]?.file || "",
  });
}

return items.map(i => ({ json: i }));
```
4. `If` block    
        Condition 1: `{{ $json.newEditionTitle }}` is not empty    
        Condition 2: `{{ $json.editionTitle }}` is not equal to `{{ $json.newEditionTitle }}`    

5. HTTP Request    
        PUT `http://{local plex IP}:32400/library/metadata/{$json.ratingKey}}`    
        Auth Type:    
            Generic Credential > Header Auth    
            Header: `X-Plex-Token`: {your Plex token}    
    
This has worked for me, and I'm happy to talk through/show bits in discord!    
        