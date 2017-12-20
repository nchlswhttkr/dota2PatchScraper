# dota2PatchScraper

![OSfrog](https://static-cdn.jtvnw.net/emoticons/v1/81248/1.0) le balanced scraper widget ![OSfrog](https://static-cdn.jtvnw.net/emoticons/v1/81248/1.0)

A small (but continually growing) patch generator for DotA2 sub-patches.

Many thanks to Valve for their font "Radiance", the Steam API and various artworks/icons. And of course for all of their work on DotA2!

## Requirements

[LXML](http://lxml.de)
[requests](http://docs.python-requests.org/en/master/)

```
pip install -r requirements.txt
```

A key to the [Steam API](http://steamcommunity.com/dev) is not required, but can be used to get updated hero and item data.

## Use

The script can be imported into existing projects or called via the command line (currently under development, and not completely tested).

#### Importing in an existing project
```
from dota2ps import DOTAPatch
```

#### CLI
```
python dota2ps.py
> http://www.dota2.com/news/updates/29717

OR

python d2ps.py http://www.dota2.com/news/updates/29717
```

## Documentation

Required arguments are indicated by **bold**, otherwise they are optional and will default.

#### DOTAPatch()
| args | type | description |
| :---: | :---: | --- |
| \* **patch_url** | string | The URL of the patch to be loaded |
| steam_api_key | string | Providing an API key will allow checks about game data (heroes/items) to be made |
| patch_directory | string | The directory to save downloaded patches to, defaults to the current working directory |
| media_directory | string | The directory to read/write media from (icons/backgrounds), defaults to the current directory. It is not recommended that you attempt to modify this, as required files are held here. |
\* *The full URL should currently be used, including protocol*

#### DOTAPatch.generate_patch()
| args | type | description |
| :---: | :---: | --- |
| generate_json | bool | True by default, will generate an accompanying ```.json``` file with the patch |
| check_for_icons | bool | False by default, will run additional check for any missing icons and downloading them from the Steam CDN |
| open_on_completion | bool | False by default, will open the patch in your default browser once it has been generated |


## Sample Patch Notes

![7.06C](./samples/706C.jpg)

![7.06D](./samples/706D.jpg)
