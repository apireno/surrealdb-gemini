# SurrealDB x Gemini: A Chat Playground

Hey there! This is a Fork of Ce11an's OpenAI<>SurrealDB demo. 

You've just stumbled upon a cool little project that's all about mashing up the brilliance of Gemini with the database wizardry of SurrealDB. Think of this as a sandbox where we're diving deep into the realms of Retrival Augmented Generation (RAG) by mixing up a large dataset of SurrealDB's documentation articles with some fancy vector storage and search capabilities.


## So, What's the Big Idea?

We're on a mission to explore the frontiers of what's possible when you pair up SurrealDB with Gemini. We're talking about importing a whopping, umm handful, of SurrealDB documentation articles, complete with their vectors, and then whipping up a RAG question-answering system that's as cool as it sounds.

We've got a cozy little FastAPI server acting as our backstage crew, Jinja2 spinning up the templates, and htmx making our frontend chat application as lively as a chat at your favorite coffee shop.

## Gear Up

Before diving in, here's what we're playing with:

- A shiny Apple M2 Pro running MacOS Sonoma 14.4
- SurrealDB 1.3.0, cozied up on disk
- Python 3.11, because we like to keep things fresh

Hit a snag? Just holler, and we'll sort it out together.

## Getting the Party Started

First off, make sure SurrealDB is ready to rock on your machine (check out [how to get it up and running](https://surrealdb.com/install)). For Python 3.11, [pyenv](https://github.com/pyenv/pyenv) is your best buddy.

Grab this repo with:

```bash
git clone https://github.com/apireno/surrealdb-gemini.git
```

You're gonna need an Gemini API key for this shindig. Not sure where to snag one?  TBD

```sql
DEFINE FUNCTION IF NOT EXISTS fn::get_gemini_token() {
    RETURN "<your-secret-key-here>"
};
```

*Heads up:* This is all for kicks and not meant for the production grind. Keep your Gemini API key under wraps!

### Setting Up SurrealDB

With your setup ready, hit up some `make` commands to get SurrealDB into gear:

Fire up SurrealDB for some on-disk action:

```bash
make surreal-start
```

To lay down the database blueprint with table and function definitions:

```bash
make surreal-init
```

Need a clean slate? Here's how to clear your database:

```bash
make surreal-remove
```

### Python Time

Jump into the Python virtual environment:

```bash
source venv/bin/activate
```

Get all the project goodies installed:

```bash
pip install -e .
```

### Grabbing the Dataset

We're going for the use SurrealDB's documentation git repository to pull some articles and generate vector embeddings (https://github.com/surrealdb/docs.surrealdb.com). Ready to download it?

```bash
get-data
```

### Populating SurrealDB

Time to move that dataset into SurrealDB:

```bash
surreal-insert
```

### Let's Do Some RAG!

Dive into SurrealDB with SurrealQL:

```bash
make surreal-sql
```

And here's a taste of what you can do with a RAG operation:

```sql
RETURN fn::surreal_rag("gemini-pro", "What is a RELATE statement about?", 0.4);
```

### Let's chat?

To start chatting with the RAG:

```
make server-start
```

## Extra Bits

Beyond the RAG adventure, feel free to query, explore, and play with the data in any way you fancy. And if you're looking to amp up your game, tools like LangChain are there to spice things up.

## Features! More features!

- [ ] Handle them darn errors! Reply with a system message that informs the user there has been an oopsie.
- [ ] Add user chat history as context.
- [ ] There are way too many steps to get started - docker-compose?
- [ ] Perform RAG to generate SurrealQL QA - this I will need help with.
- [ ] Ummm where are the tests? You, the user, are the test! (seriously, I need to add some...).

## Coffee, Anyone?

If this little project made your day or saved you a coffee break's worth of time, consider fueling Ce11an's caffeine love:

<a href="https://www.buymeacoffee.com/ce11an" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

