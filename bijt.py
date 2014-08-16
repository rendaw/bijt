#!/usr/bin/env python2
from __future__ import print_function
import json, os, sys, argparse, re, itertools

def die(message):
    print('ERROR: {}'.format(message), file=sys.stderr)
    sys.exit(1)

def check(context, state, template):
    if isinstance(template, basestring) and context['save_re'].match(template):
        if template in state['saved']:
            return (False, u'Save \'{}\' appears multiple times.')
        state['saved'].add(template)
    elif isinstance(template, list):
        for subtemplate in template:
            result = check(context, state, subtemplate)
            if not result[0]:
                return result
    elif isinstance(tree, dict):
        if isinstance(template, dict):
            for key, subtemplate in template.items():
                result = check(context, state, subtemplate)
                if not result[0]:
                    return result
    return (True, None)

def render(context, state, template=None):
    if template == None:
        template = state['render_template']
    if isinstance(template, basestring) and context['save_re'].match(template):
        return state['saved'][template]
    if isinstance(template, list):
        for i, subtemplate in enumerate(template):
            template[i] = render(context, state, subtemplate)
    elif isinstance(template, dict):
        for k, subtemplate in template.items():
            template[k] = render(context, state, subtemplate)
    return template
    
def subtransform(context, state, template=None, tree=None, top=True):
    if template == None or tree == None:
        return False
    if isinstance(template, basestring) and context['save_re'].match(template):
        state['saved'][template] = tree
        return True
    if isinstance(tree, list):
        if isinstance(template, list):
            if all(
                    subtransform(context, state, subtemplate, subtree, top=False) 
                        for subtemplate, subtree in itertools.izip_longest(template, tree, fillvalue=None)
                ):
                return True
        if top:
            for i, subtree in enumerate(tree):
                if subtransform(context, state, template, subtree):
                    tree[i] = render(context, state)
    elif isinstance(tree, dict):
        if isinstance(template, dict) and len(tree.keys()) == len(template.keys()):
            all_matched = True
            for k in tree.keys():
                if k not in template:
                    all_matched = False
                    break
                if not subtransform(context, state, template[k], tree[k], top=False):
                    all_matched = False
                    break
            if all_matched:
                return True
        if top:
            for k, subtree in tree.items():
                if subtransform(context, state, template, subtree):
                    tree[k] = render(context, state)
    elif tree == template:
        return True
    return False

def transform(transformations, tree, reverse=False):
    escaped_delimeter = ''.join(u'\\' + c for c in transformations['delimeter'])
    context = {
        'save_re': re.compile(escaped_delimeter + u'.*' + escaped_delimeter)
    }
    for i, transformation in enumerate(transformations['transformations']):
        if reverse:
            transformation['to'], transformation['from'] = transformation['from'], transformation['to']
        to_state = {'saved': set()}
        from_state = {'saved': set()}
        result = check(context, from_state, transformation['from'])
        if not result[0]:
            die(u'Invalid from template for transformation {}: {}'.format(i, result[1]))
        result = check(context, to_state, transformation['to'])
        if not result[0]:
            die(u'Invalid from template for transformation {}: {}'.format(i, result[1]))
        if to_state['saved'] != from_state['saved']:
            die(u'Transformation {} has mismatched saved:\nfrom: {}\nto: {}'.format(i, from_state['saved'], to_state['saved']))
        transform_state = {
            'saved': {}, 
            'render_template': transformation['to']
        }
        if subtransform(context, transform_state, transformation['from'], tree):
            tree = render(context, transform_state)
    return tree

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('transformations', help='The transformations file')
    parser.add_argument('document', help='The document to transform')
    parser.add_argument('-r', '--reverse', help='Apply transformations in reverse, swapping to and from', action="store_true")
    args = parser.parse_args()
    transformations = json.loads(open(args.transformations, 'r').read())
    tree = json.loads(open(args.document, 'r').read())

    tree = transform(transformations, tree, reverse=args.reverse == 1)

    print(json.dumps(tree, indent=4))

