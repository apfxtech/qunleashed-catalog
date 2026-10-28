# Submission

- Kind: app / menu style / animation (keep one)
- [ Describe your submission here - its features or what has changed since the last version ]


# Extra Requirements

- [ Describe if your submission requires any extra hardware or software ]


# Author Checklist (Fill this out)

- [ ] I've read the [contribution guidelines](../blob/HEAD/documentation/Contributing.md) and my PR follows them
- [ ] I own the code I'm submitting or have code owner's permission to submit it
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] The manifest pins `commit_sha`; only a repository in `trusted.yml` may leave it to app-stream
- [ ] I [have validated](../blob/HEAD/documentation/Manifest.md#validating-manifest) the manifest file(s) with `python3 tools/publish.py check --build <path>/manifest.yml`

# AI usage disclosure (Fill this out)

Keep the ONE option below that matches your submission and DELETE the other two.

- No AI was used - all code was written by hand.
- Partially AI assisted - clarify below which parts were AI assisted and briefly explain what they do.
- Fully AI generated - explain what all the generated code does in moderate detail.

- [ If AI was used, describe how here. Delete this line if no AI was used. ]

# Reviewer Checklist (Don't fill this out, and don't remove it from the template)

- [ ] Bundle is valid
- [ ] There are no obvious issues with the source code
- [ ] A manifest without `commit_sha` points to a trusted repository
- [ ] I've ran this submission and verified its functionality
