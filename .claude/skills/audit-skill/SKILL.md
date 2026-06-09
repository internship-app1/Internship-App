---
name: audit-skill
description: The purpose of this skill is to understand how the code base works and understand the archetiure of Internship Matcher.
---


## Step 0 -- The goal / context:

The point of this skill is that the user, sujan has basically let multiple claude code sessions decide the archeiture of Internship Matcher, and now he is has no clue how Internship Matcher works. This is an issue because:

** 1 He has a harder time fixing bugs if they arise, beacuse he needs to again understand how the archeiture workk, and then see what components broken and fix it using some archeiture suggested by claude. 

** 2 He has a hard time describing the archeiture to himself and others (like say an interviewer who asks about it). This is fundementally bad, because any busisness person or founder MUST know the MOST about their product and clearly sujan is just a visionary and not an archeitect.

# Now the goals

The goals of this skill

* Help sujan understand in depth the archeiture of this code base by:
- explaining in simple terms about the code base. Think of Sujan as a junior swe engineer. Explain the archeiture to him. The goal of this skill is to make him understand the entire archeiture end to end, so he can be bumped to a senior software engineer
- quiz him on archetiture. Grill him like how a senior engineer does during code review. Make sure he goes IN DEPTH when describing the archeiture. 


## Step 1 -- Internship matcher

Internship matcher is a product intended for college students studying computer science/ comp E / physics / etc. who are all intending to land SWE intern roles. The way the product is intended to work is that the user uploads their resume, and they get jobs matched to their resume + projects + experience and their impact.

## Step 2 -- Handle a lot of users

Since we are making a lot of LLM calls and claude calls, we need to find better ways to handle this, because if we have 5-10 active users at a second, then it brings a lot of traffic and a fuck ton of LLM calls to Anthropic, so one of the goals is basically finding more cost effective ways to get this done, maybe switching to cheaper models or even local models.

## Step 3 -- This skill is intended for ALL contributors of this code base.

Fill them in on future plans, the archeiture of Internship Matcher. Help them debug from small things like how to get started with Internship matcher, all the way to contributing, to PRs and passing the Backend and Frontend tests we have in check for the user.

 
