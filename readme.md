# Memrise resources

* [Python script](#python)
  * [JSON format](#json)
    * [The ```settings``` object](#json_settings)
    * [The ```subsets``` object](#json_subsets)
      * [Rendering specification](#json_rendering)
* [Devanāgarī resources](#devanagari)

This is a collection of resources I have gathered for several (image based) [Memrise](https://www.memrise.com/) courses, that teach alphabets such as Devanāgarī.

## <a name="python"></a>Python script
This is a script that generates&nbsp;PNGs for a set of character, as specified in a JSON file. It calls [ImageMagick](https://www.imagemagick.org/) for creating the&nbsp;PNGs and uses either [Pango](https://developer.gnome.org/pango/stable/PangoMarkupFormat.html) or&nbsp;[XeLaTeX](https://en.wikipedia.org/wiki/XeLaTeX) to render the characters.

```
usage: generate-from-json.py [-h] --engine {pango,xelatex}
                             JsonSpecificationFile
```


### <a name="json"></a>JSON format
The JSON specification consists has two main attributes: ```settings``` and&nbsp;```subsets```. They are further specified below. The top level structure of the&nbsp;JSON&nbsp;file is therefore:
```javascript
{
  "settings": {...},
  "subsets": {...}
}
```

#### <a name="json_settings"></a>The ```settings``` object
This contains specific settings for the data set:
* The name for this character set (which will be used to create an output directory)
* The default font (optional) to be used for rendering
* A skeleton for the Pango argument string to be fed to ImageMagick (in the case that the Pango rendering mode is selected at the command line).
* A skeleton for the XeLaTeX code to be executed to an intermediate PDF (in the case that the XeLaTeX rendering mode is selected at the command line).

For the latter two, the character string to be rendered will be inserted into the skeleton string at the point marked by&nbsp;```{0}``` and the font name will be inserted at the point marked by&nbsp;```{1}```.
```javascript
{
  "name": "Devanāgarī", 
  "defaultFont": "Siddhanta",
  "pango": "pango:<markup><span font_family=\"{1}\" size=\"192000\"> {0} </span></markup>",
  "xelatex": "\\documentclass{{minimal}}\n\\usepackage{{fontspec}}\n\\usepackage{{xcolor}}\n\\setmainfont[Script=Devanagari]{{{1}}}\n\\begin{{document}}\n{0}\n\\end{{document}}"
}
```

#### <a name="json_subsets"></a>The ```subsets``` object
This contains subsets of character data, all to be rendered to individual subfolders. Each subset is an array of character string objects.

Each character string object is identified by a&nbsp;```name``` and can have multiple ```renditions```, i.e.&nbsp;an array of multiple rendering specifications (see more below). It can have an optional attribute&nbsp;```alts``` to record any alternative names in an array of strings (for Memrise), but the script at present does nothing with this information.

```javascript
{
  "vowels":
  [ 
    {
      "name": "a",
      "renditions": [
        { "utf8": "अ" }, 
        { "utf8": "अ", "font": "Siddhanta2" } 
      ]
    },
    {
      "name": "ā",
      "renditions": [
        { "utf8": "आ" }, 
        { "utf8": "आ", "font": "Siddhanta2" } 
      ]
    }
  ],
  "consonants": [...]
}
```
##### <a name="json_rendering"></a>Rendering specification
As can be seen above, the rendering specification in its most basic form contains only a&nbsp;UTF-8 string. A&nbsp;```font``` can be specified, but if it is absent, the&nbsp;```defaultFont``` specified in the&nbsp;```settings``` is simply fallen back on.

Instead of a&nbsp;UTF-8 string, the specification can also contain an explicit ```pango``` or ```xelatex``` code string to be used instead (in their respective modes). In the case of Pango rendering mode, also the attributes ```pango-flip``` and ```pango-flop``` are available and if set to true, will be set as flags for the rendering call to pango (which will flip the image in the vertical or horizontal direction, respectively).

```javascript
{
  "name": "a-mirrored",
  "renditions":
  [
    {
      "utf8": "अ",
      "pango-flop": true,
      "xelatex": "\\reflectbox{अ}"
    }
  ]
},
{
  "name": "a-red",
  "renditions":
  [
    {
      "pango": "<span color=\"red\">अ</span>",
      "xelatex": "{\\color{red}अ}"
    }
  ]
}
```

Note that&nbsp;– depending on the rendering mode&nbsp;– at least one of the attributes ```utf8```, ```pango``` or&nbsp;```xelatex``` should be present.


## <a name="devanagari"></a>Devanāgarī resources
The associated Memrise course is [Sanskrit devanāgarī](https://www.memrise.com/course/231917/sanskrit-devanagari/).
* [This pdf](devanagari/gonda/gonda.pdf) contains a digitized version of the first chapter of Jan Gonda's [_A Concise Elementary Grammar of the Sanskrit Language_](http://www.uapress.ua.edu/product/Concise-Elementary-Grammar-of-the-Sanskrit-Languag,261.aspx) (2nd edition, 2006, ISBN-13 978-08173-5261-5), in which the devanāgarī script is introduced.
Unfortunately, even the most recent printed edition of this book is only a facsimile of the 1966 original. For that reason, some of the devanāgarī characters are either hard to read or awkwardly typeset (see also the original on [google books](https://books.google.nl/books?id=wCwVAAAAIAAJ&lpg=PP1&pg=PA1#v=onepage)). For that reason I found it reasonable to reproduce that part, using more modern technology (like Unicode fonts) so it can be properly read.
* The fonts used for generating the images for Memrise (as well as in the document mentioned above) are mainly those of the _Siddhanta_ font family, created by [Mihail Bayaryn](https://sites.google.com/site/bayaryn/) (Міхаіл Баярын) and available from his site under a [Creative Commons license](http://creativecommons.org/licenses/by-nc-nd/3.0/).
* Honourable mention is for the program [Itranslator&nbsp; 2003](https://www.oah.in/Sanskrit/itranslator2003.htm), which is a great help for transliterating ASCII text in [ITRANS notation](https://en.wikipedia.org/wiki/ITRANS) to devanāgarī text. Its font _Sanskrit&nbsp;2003_ helped to create an earlier version of the course.