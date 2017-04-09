# e621sync

Really simple python project to download files from e621.net based on tags


## features

  * Multi-threaded downloads
  * Supports multiple rules each with their own tags and download locations
  * That's it...


## requirements

 * Python 3  (tested using Python 3.4/3.5 on Windows and Linux)


## install

    pip install -r requirements.txt
    cp config.sample.toml config.toml
    
    
## configuration

All settings live in `config.toml` and are documented there.

Lines beginning with `#` are comments and are not read by the program. 

To create a new rule simple follow this template:

    [rule.UniqueTagName]
    tags = ["this", "that"]
    download_directory = "./downloads/new_stuff/"

The rule name (e.g. `UniqueTagName`) itself isn't important, it should just be unique.  You can include spaces in name 
too e.g. `[rule."Proper Sentence"]`.

You can override the global `minimum_score` and `blacklist_tags` in each rule

If the tags contain `pool:` all other options are ignored and the entire pool is downloaded (the the index of the item 
prefixed to the filename)

The file format is in TOML, if you want more information about the syntax see:

 * https://github.com/toml-lang/toml


## running

    python e621sync.py

    
## notes

1. Downloaded file names are hard coded to `"{id}_{md5}.{ext}"`

2. Every run all items are re-checked and re-downloaded if missing.  There is no id, or date checks to only update new
files.

3. ctrl+c does not work very well  (ctrl+break may help).