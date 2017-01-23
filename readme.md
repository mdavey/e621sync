# e621sync

Really simple python project to download files from e621.net based on tags

Downloaded file name is hard coded to `"{id}_{md5}.{ext}"`


## requirements

 * Python 3  (tested using Python 3.4)


## install

    pip install -r requirements.txt
    cp config.toml.sample config.toml
    
    
## configuration

All settings live in `config.toml` and are documented there

To create a new rule simple follow this template:

    [rule.NewStuff]
    tags = "this -that"
    download_directory = "./downloads/new_stuff/"

## running

    python e621sync.py