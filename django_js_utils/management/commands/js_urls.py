import sys
import re

from django.core.urlresolvers import RegexURLPattern, RegexURLResolver
from django.core.management.base import BaseCommand
from django.utils import simplejson
from django.utils.datastructures import SortedDict
from django.conf import settings as project_settings

from django_js_utils import settings as app_settings

from django.db import models
import re


RE_KWARG = re.compile(r"(\(\?P\<(.*?)\>.*?\))") #Pattern for recongnizing named parameters in urls
RE_ARG = re.compile(r"(\(.*?\))") #Pattern for recognizing unnamed url parameters
    
# If you access your app with some prefix; blank otherwise
_PREFIX_ = '/app_name/'


# List of apps used in this project -- used to filter the URLs generated in the JS file
APPS_LIST = ('app1', 'app2',)
FILTER_PATTERNS = []

# Compile the URL patterns to be excluded
for app in APPS_LIST:
    FILTER_PATTERNS.append(re.compile(r'^%s_.*_add$' % app))
    FILTER_PATTERNS.append(re.compile(r'^%s_.*_history$' % app))
    FILTER_PATTERNS.append(re.compile(r'^%s_.*_delete$' % app))
    FILTER_PATTERNS.append(re.compile(r'^%s_.*_change$' % app))
    FILTER_PATTERNS.append(re.compile(r'^%s_.*_changelist$' % app))

# Some admin URLs to skip
FILTER_PATTERNS.append(re.compile(r'^app_list$'))
FILTER_PATTERNS.append(re.compile(r'^logout$'))
FILTER_PATTERNS.append(re.compile(r'^jsi18n$'))
FILTER_PATTERNS.append(re.compile(r'^password_change$'))
FILTER_PATTERNS.append(re.compile(r'^password_change_done$'))

for label in ['user', 'group']:
    for action in ['add', 'change', 'changelist', 'delete', 'history']:
        FILTER_PATTERNS.append(re.compile(r'^auth_%s_%s$' % (label, action,)))
    

    
class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        Create urls.js file by parsing all of the urlpatterns in the root urls.py file
        """
        js_patterns = SortedDict()
        print "Generating Javascript urls file %s" % app_settings.URLS_JS_GENERATED_FILE
        Command.handle_url_module(js_patterns, project_settings.ROOT_URLCONF)
        #output to the file
        urls_file = open(app_settings.URLS_JS_GENERATED_FILE, "w")
        urls_file.write("dutils.conf.urls = ")
        simplejson.dump(js_patterns, urls_file, separators = (',\n', ':'))
        print "Done generating Javascript urls file %s" % app_settings.URLS_JS_GENERATED_FILE
    
    @staticmethod
    def handle_url_module(js_patterns, module_name, prefix=""):
        """
        Load the module and output all of the patterns
        Recurse on the included modules
        """
        if isinstance(module_name, basestring):
            __import__(module_name)
            root_urls = sys.modules[module_name]
            patterns = root_urls.urlpatterns
        else:
            root_urls = module_name
            patterns = root_urls

        for pattern in patterns:
            if issubclass(pattern.__class__, RegexURLPattern):
                if pattern.name:
                    full_url = prefix + pattern.regex.pattern
                    for chr in ["^","$"]:
                        full_url = full_url.replace(chr, "")
                    #handle kwargs, args
                    kwarg_matches = RE_KWARG.findall(full_url)
                    if kwarg_matches:
                        for el in kwarg_matches:
                            #prepare the output for JS resolver
                            full_url = full_url.replace(el[0], "<%s>" % el[1])
                    #after processing all kwargs try args
                    args_matches = RE_ARG.findall(full_url)
                    if args_matches:
                        for el in args_matches:
                            full_url = full_url.replace(el, "<>")#replace by a empty parameter name
                    # Changed by Barun
                    # js_patterns[pattern.name] = "/" + full_url
                    skip_this_url = False
                    for filter_pattern in FILTER_PATTERNS:
                        if filter_pattern.match(pattern.name):
                            skip_this_url = True
                            break

                    if not skip_this_url:
                        print pattern.name
                        js_patterns[pattern.name] = _PREFIX_ + full_url
                    # End change
            elif issubclass(pattern.__class__, RegexURLResolver):
                if pattern.urlconf_name:
                    Command.handle_url_module(js_patterns, pattern.urlconf_name, prefix=pattern.regex.pattern)
