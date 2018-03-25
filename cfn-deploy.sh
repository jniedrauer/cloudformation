#!/usr/bin/env bash

set -eu

stack="${1%/}"
wd="$(pwd)"
build=build

. "$wd/config/${ENV:-dev}.cfg"

main() {
    render_templates

    validate_templates

    diff_templates

    cfn_sync

    cfn_stack=${stack##*/}

    if stack_exists; then
        update_stack
    else
        create_stack
    fi
}

render_templates() {
    meta/render.py -i "$wd/$stack" -o "$build/$stack"
}

validate_templates() {
    find "$build/$stack" -type f -name '*yml' -print0 \
        | while IFS= read -r -d '' f; do
            echo "Validating: $f"
            aws cloudformation validate-template --template-body "file://$f"
        done
}

diff_templates() {
    mkdir -p "$build/.tmp/$stack"
    aws s3 sync "s3://$CFN_BUCKET/$stack/" "$build/.tmp/$stack/"
    find "$build/$stack" -type f -name '*yml' -print0 \
        | while IFS= read -r -d '' f; do
            echo "Comparing: $f"
            diff_template "$f"
        done

    read -rp 'Continue deploy? [y/N]: ' answer
    grep -iq '^y' <<<"$answer" || exit 0
}

diff_template() {
    new="$1"
    basename=${new##*/}
    rendered="$build/.tmp/$stack/$basename"
    test -f "$rendered" && old="$rendered" || old=/dev/null
    diff -u --color "$old" "$new" || true
}

cfn_sync() {
    aws s3 sync "$build/$stack/" "s3://$CFN_BUCKET/$stack/" \
        --exclude '*' --include '*.yml'
}

stack_exists() {
    aws cloudformation describe-stacks \
        --stack-name "$cfn_stack" >/dev/null 2>&1
}

update_stack() {
    aws cloudformation update-stack \
        --stack-name "$cfn_stack" \
        --template-body "file://$build/$stack/main.yml" \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameters "ParameterKey=StackName,ParameterValue=$stack"
}

create_stack() {
    aws cloudformation create-stack \
        --stack-name "$cfn_stack" \
        --template-body "file://$build/$stack/main.yml" \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameters "ParameterKey=StackName,ParameterValue=$stack"
}

main
