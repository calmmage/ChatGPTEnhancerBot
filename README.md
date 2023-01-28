# Branches:

main - most stable version. Only released after tested in beta. @ChatGPTKitBot
beta - current beta version. @ChatGPTEnhancerBot
dev - most unstable. Whatever we're currently experimenting with. Might be broken. @PetrLavrovTestBot

# Development plan

1) Functional: Support commands in telegram
2) Purpose. Request/topic support for the conversation
3) Initial interview - to get to know the user. Save as a context for General chat
4) Functional: support "context" for each conversation
    1) Attach to each query
    2) Update context with time to reflect new developments in conversation..
    3) URGENT: compress conversation history into context bullet points every 10 messages or so - to avoid excessive
       history accumulation
5) add logging to file / ELK

# Features ideas

1) Purpose. Let user specify (or bot - guess) goal of request

- Advice
- Emotional support
- Clarification
  How to do?
  "Please respond to this message so that the response exactly fits the stated purpose and doesn't include anything
  that's not it
  Purpose: Emotional support, like you're calling a friend.
  Message: I got fired from work"

"Purpose: Emotional support, like you're calling a friend. Message: [user's message]"
In this case, you are asking ChatGPT to generate a response that is similar to what a friend might say to offer
emotional support. This could include words of encouragement, empathy, and reassurance.

"Purpose: Emotional support, like you're talking to a therapist. Message: [user's message]"
In this case, you are asking ChatGPT to generate a response that is similar to what a therapist might say to offer
emotional support. This could include active listening, validation, and guidance on coping strategies.

"Purpose: Emotional support, like you're writing in a journal. Message: [user's message]"
In this case, you are asking ChatGPT to generate a response that is similar to what a person might write in a journal to
offer themselves emotional support. This could include self-compassion, self-reflection, and affirmations.

2) Continuity. Let the bot rememeber...

- content of your past converstaions?
- general information about yourself?
- Some extra info from other areas (e.g. like Siri)

How to do? Chat history!

- Option 1: have general conversation thread. clean it up sometimes / summarize chunks
    - IDEA: Include datetime for bot! So that it knows if a lot of time passed!
    - Alternatively - roll over to a new chat once a lot of time passed.
    - Alternatively - indicate to a bot once new conversation started
- Option 2: continue the last conversation (forgets older stuff :( ))

3) Reach out to user randomly. (Generate prompt by gpt)

# Quick Notes - Inbox

1) Try Use another model - davinci-instruct-beta:2.0.0 ! This is the predecessor of chatgpt!
2) Try unofficial chatgpt api
3) Delay response messages - or send unsolicited messages. Or split messages in part
   Imitate real human!!
4) React with Emoji!