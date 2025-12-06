# TPN: A cheap BASIC cross-transpiler for the MEGA65

In 2021, MEGA65 developer ubik created the Eleven on-device integrated programming environment for the MEGA65. Eleven is a *transpiler* for BASIC 10, the version of BASIC included with the Commodore 65. As a programming language, it is similar to BASIC, with only a few but important ergonomic features: long variable names, labels, optional line numbers, and a low-profile comment syntax. The Eleven IDE included a featureful text editor, and a build workflow that output standalone BASIC 10 programs that could be distributed and run on any MEGA65. From 2022 to present day, MEGA65 team member Gurce has been maintaining Eleven, adding features, fixing bugs, and improving performance. See [the MEGA65 Eleven Github repo](https://github.com/MEGA65/eleven) for the latest code.

```
' a simple Eleven program

#declare degrees$
#declare degrees
#declare units$

.start
    input "how many degrees";degrees$
    degrees = val(degrees$)
    input "units (c/f)";units$
    if units$ <> "c" and units$ <> "f" then .start
    gosub convert
    print "result: ";degrees;" ";units$
    end

.convert
    if units$ = "f" then convert_f_to_c
    ' convert c to f
    degrees = degrees * 9/5 + 32
    units$ = "f"
    return

.convert_f_to_c
    degrees = (degrees - 32) * 5/9
    units$ = "c"
    return
```

TPN is a cross-transpiler with syntax similar to Eleven. It does not run directly on the MEGA65, one of Eleven's most important features. Instead, it's just a way to generate BASIC 65 PRG files on a PC for use on a MEGA65.

The primary goal of TPN is to allow cross-development of Commodore BASIC programs without the syntax hindrances of CBM BASIC that are required by the transpiler `petcat`, especially line numbers. TPN takes a source file in an Eleven-like syntax and converts it to BASIC 65 text. You can then feed this text to `petcat` to produce a PRG file. That's it.

A secondary goal of TPN is for the generated BASIC text to be readable by humans directly on the MEGA65, as a code sample. TPN tries to pick sensible line numbers and two-character variable names, and does not crunch interior space.

It is not a goal for TPN to support all Eleven source files, or track development of the Eleven project. I just wanted something roughly similar. It probably comes close, but it's only marginally useful to interoperate with Eleven.

You can use TPN to make BASIC programs for other Commodore computers supported by `petcat`. Currently, TPN reserves all MEGA65 BASIC keywords, so they cannot be used as long variable names.

"TPN" stands for "Ten Point Nine," which isn't anything but I was in a hurry and didn't put much thought into it.

## Set-up

TPN is written in Python 3, and Python must be installed. No other tools are needed.

You probably want to install `petcat` to convert the output of TPN to a PRG file. `petcat` is distributed with the [VICE suite](https://vice-emu.sourceforge.io/) of Commodore emulators, or you can [download it from MEGA65 Filehost](https://files.mega65.org?id=9561505c-a36d-4d3e-b158-d52a718e818e).

## Usage

Run the `tpn.py` Python script with your TPN source filename as an argument, or the source text written to the input channel. `tpn.py` writes the generated BASIC to the output channel. On command shells that support pipes, you can pass this to `petcat` in a single command, like so.

```
python3 tpn.py mysource.bas | petcat -w65 -o myprogram.prg
```

## Supported features of Eleven

* Low-profile line comment syntax: `' comment`
* Line labels: `.label` ; `goto label`
* Long variable names, must be declared before use:
    * `#declare floatingPointVariable`
    * `#declare stringVariable$`
    * `#declare integerVariable%`
    * `print stringVariable$;" = ";(floatingPointVariable * 3)`
* Array dimension shorthand: `#declare anArray(100)`
    * Equivalent to `#declare anArray` ; `dim anArray(100)`
* Variable initialization shorthand: `#declare eleven = 11`
* Preprocessor constants: `#define CONSTNAME = 11`
* Conditional transpilation: `#ifdef CONSTNAME` ; `#endif`
* Optional line numbers: starting a line with a number resets the line number generator.
    * This is not smart, and will generate out of order or redundant line numbers if you ask it to.

*All* variables must be declared before use. To help catch typos, TPN reports undeclared variables as errors.

## Additional features

Both the input and output are ASCII text, with the expectation that the ASCII file will be passed to `petcat`. This includes support for magazine-style PETSCII conversions in string literals. TPN does not transform string contents for any reason, so you can use whatever style you like, and provide matching arguments to `petcat`.

To stay compatible with Eleven source files, `#output "..."` is ignored.

`tpn.py` accepts input on stdin, so you can pipe in source text another way.

```
make_tpn_source | python3 tpn.py | petcat -w65 -o myprogram.prg
```

You can also specify multiple source filenames on the command line, to spread your program out across multiple input source files. The result is always one contiguous BASIC program listing, in the order the input files were provided. This can be useful for build workflows. For example, you could have different "header" files with `#define` directives, and a shared main source file with `#ifdef` and constants, and build different versions of the same program.

```
python3 tpn.py debug_header.bas myprogram.bas | python3 tpn.py

python3 tpn.py release_header.bas myprogram.bas | python3 tpn.py
```

It could also be used for reusable libraries of labeled subroutines.

```
python3 tpn.py graphicslib.bas musiclib.bas myprogram.bas | python3 tpn.py
```

## Future?

An `#import` statement would be more useful than the concatenation examples above.

Add a command-line option to select the target BASIC dialect, so as to reserve the matching keyword set. (TPN already works with other BASIC dialects, such as C64 BASIC 2.0, if you don't mind the BASIC 65 keywords being reserved unnecessarily.)
