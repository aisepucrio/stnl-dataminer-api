#!/bin/sh

# Load environment variables from .env file
[ ! -f .env ] || export $(grep -v '^#' .env | xargs)
