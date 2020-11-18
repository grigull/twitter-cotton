#!/usr/bin/env python3

from aws_cdk import core

from twitter_cotton.twitter_cotton_stack import TwitterCottonStack


app = core.App()
TwitterCottonStack(app, "twitter-cotton")

app.synth()
