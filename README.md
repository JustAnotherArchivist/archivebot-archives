# archivebot-archives
This repository contains a list of files in the [ArchiveBot collection on Internet Archive](https://archive.org/details/archivebot) and the corresponding code.

The `archives` directory contains one YAML file per item in the collection, listing all files in the item (including their size and modification date). It is updated automatically every 6 hours.

The `code` directory contains the code behind this data acquisition. It uses the [internetarchive](https://github.com/jjjake/internetarchive) library for communicating with the Internet Archive.
