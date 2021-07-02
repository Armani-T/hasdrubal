# Hasdrubal README

[![License](https://img.shields.io/github/license/Naereen/StrapDown.js.svg)](https://github.com/Naereen/StrapDown.js/blob/master/LICENSE) [![Made with Python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/) [![Build Status](https://travis-ci.com/Armani-T/hasdrubal.svg?branch=main)](https://travis-ci.com/Armani-T/hasdrubal)

```
|-|   |-|                      |-|                  |-|              |-|
| |   | |                      | |                  | |              | |
| |___| |                      | |                  | |              | |
| _____ |   ____  +-----|   ___| | |-|____ |-|  |-| | |___     ____  | |
| |   | |  / _  | | ----+  / __  | | +---- | |  | | |  _  \   / _  | | |
| |   | | | (_| | +____ | | (__| | | |     | |__| | | |_)  | | (_| | | |
|_|   |_|  \__,_| |_____|  \_____| |_|     |____,_| |_____/   \__,_| |_|
```

A general-purpose functional programming language built around making algebraic-effects practical.

Algebraic effects are a new method of adding impurity to purely functional languages using continuations. In practice, they act like exceptions in imperative languages but you can use them for anything from I/O to mutable state to regular exceptions.

### Features

I plan for the language to have (at least) these features:

- First class functions
- Hindley-Milner type inference but extended to infer effects too
- Algebraic Data Types
- Sum types
- Haskell-style type classes
- Fiber-based concurrency
- An OCaml-style module system

## Installation

Here's how to get it on your machine:

```bash
git clone https://github.com/Armani-T/hasdrubal
cd hasdrubal
```

At the moment, the language is not fully implemented so it cannot run any code but that will change very soon.

You can check if it's working by running `python hasdrubal --version`. If it installed properly, it should print out `Hasdrubal Version 0.0.1`

## Development Setup

Just follow  the above steps but before working on the code also run:

```bash
pip install -r requirements-dev.txt
```

## Contributing

Please use GitHub issues for bug reports and feature requests.

1. Create your feature branch by forking the `develop` branch.
3. Commit your changes.
4. Push to `origin/develop`.
5. Open a pull request.

## Notes

I'm currently working on a python implementation which will serve as the reference for a future Rust implementation in order to make it faster.

## Meta

- Name: **Armani Tallam**
- E-Mail: armanitallam@gmail.com
- GitHub: <https://www.github.com/Armani-T>

This project is licensed under the **MIT License**. Please see the [license file](LICENSE) for more information on the licensing.
