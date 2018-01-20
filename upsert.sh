#!/usr/bin/env bash

set -eux

stack="${1%/*}"
wd="$(pwd)"

main() {
    validate_stacks

    if stack_exists >/dev/null 2>&1; then
        update_stack
    else
        create_stack
    fi
}

validate_stacks() {
    find "$wd/$stack" -type f -name '*yml' -print0 | xargs -0 -I % \
        aws cloudformation validate-template \
        --template-body file://%
}

stack_exists() {
    aws cloudformation describe-stacks \
        --stack-name "$stack"
}

update_stack() {
    aws cloudformation update-stack \
        --stack-name "$stack" \
        --template-body "file://$wd/$stack/base.yml" \
        --capabilities CAPABILITY_NAMED_IAM
}

create_stack() {
    aws cloudformation create-stack \
        --stack-name "$stack" \
        --template-body "file://$wd/$stack/base.yml" \
        --capabilities CAPABILITY_NAMED_IAM
}

main
