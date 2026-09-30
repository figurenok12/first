"""Sanity checks for the edited save: XML, health on new things, duplicate ids, dangling refs."""
import re, sys, collections, xml.etree.ElementTree as ET
FN = '/home/user/first/mirella fans_edited.rws'
t = open(FN, encoding='utf-8-sig').read()
ET.fromstring(t.encode()); print('XML OK')
ids = re.findall(r'<id>([A-Za-z_]+\d+)</id>', t)
print('duplicate ids:', [k for k, v in collections.Counter(ids).items() if v > 1])
refs = set(re.findall(r'>Thing_([A-Za-z_]+\d+)<', t))
print('dangling refs:', len([r for r in refs if r not in set(ids)]))
nohp = collections.Counter()
for m in re.finditer(r'<thing Class="[\w.]+">(.*?)</thing>', t, re.S):
    b = m.group(1); i = re.search(r'<id>([A-Za-z_]+)(\d+)</id>', b)
    if i and int(i.group(2)) >= 502723 and '<health>' not in b: nohp[i.group(1)] += 1
print('new things without health:', dict(nohp))
