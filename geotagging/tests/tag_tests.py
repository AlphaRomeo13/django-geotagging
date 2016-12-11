from django import template
from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point, LineString

from geotagging.models import Geotag, HAS_GEOGRAPHY

class TagTestCase(TestCase):
    """Helper class with some tag helper functions"""
    
    def installTagLibrary(self, library):
        template.libraries[library] = __import__(library)
        
    def renderTemplate(self, tstr, **context):
        tmpl = template.Template(tstr)
        cntxt = template.Context(context)
        return tmpl.render(cntxt)

class OutputTagTest(TagTestCase):
    
    def setUp(self):
        self.installTagLibrary('geotagging.templatetags.geotagging_tags')
        denver_user = User.objects.create(username='denver')
        dia_user = User.objects.create(username='dia')
        aa_user = User.objects.create(username='annarbor')
	self.line = LineString((-104.552299, 38.128626), (-103.211191, 40.715081))
        self.denver = Geotag.objects.create(tagged_obj=denver_user,
                            point=Point(-104.9847034, 39.739153600000002))
        dia = Geotag.objects.create(tagged_obj=dia_user,
                            point=Point(-104.673856, 39.849511999999997))
        aa = Geotag.objects.create(tagged_obj=aa_user,
                            point=Point(-83.726329399999997, 42.2708716))
        
    def testOutput(self):
        "get_objects_nearby tag has no output"
        tmpl = "{% load geotagging_tags %}"\
                   "{% get_objects_nearby obj.point as nearby_objs %}"
        o = self.renderTemplate(tmpl, obj=self.denver)
        self.assertEqual(o.strip(), "")
        
    def testAsVar(self):
        tmpl = "{% load geotagging_tags %}"\
                   "{% get_objects_nearby obj.point as nearby_objs %}"\
                   "{{ nearby_objs|length }}"
        o = self.renderTemplate(tmpl, obj=self.denver)
        self.assertEqual(o.strip(), "1")

    def testShortDistance(self):
        # DIA is about 18 miles from downtown Denver
        short_tmpl = "{% load geotagging_tags %}"\
                   "{% get_objects_nearby obj.point as nearby_objs within 17 %}"\
                   "{{ nearby_objs|length }}"
        o = self.renderTemplate(short_tmpl, obj=self.denver)
        self.assertEqual(o.strip(), "1")
        long_tmpl = short_tmpl.replace("17", "19")
        o = self.renderTemplate(long_tmpl, obj=self.denver)
        self.assertEqual(o.strip(), "2")

    def testLongDistance(self):
        # Ann Arbor is about 1122 miles from Denver
        short_tmpl = "{% load geotagging_tags %}"\
                   "{% get_objects_nearby obj.point within 1115 as nearby_objs %}"\
                   "{{ nearby_objs|length }}"
        o = self.renderTemplate(short_tmpl, obj=self.denver)
        self.assertEqual(o.strip(), "2")
        long_tmpl = short_tmpl.replace("1115", "1125")
        o = self.renderTemplate(long_tmpl, obj=self.denver)
        self.assertEqual(o.strip(), "3")
        
    def testNonPoint(self):
        hit_tmpl = "{% load geotagging_tags %}"\
                   "{% get_objects_nearby line within 50 as nearby_objs %}"\
                   "{{ nearby_objs|length }}"
        miss_tmpl = hit_tmpl.replace("50", "10")
        
        if HAS_GEOGRAPHY:
            hit = self.renderTemplate(hit_tmpl, line=self.line)
            self.assertEqual(hit.strip(), "1")
            miss = self.renderTemplate(miss_tmpl, line=self.line)
            self.assertEqual(miss.strip(), "0")
        else:
            try:
                hit = self.renderTemplate(hit_tmpl, line=self.line)
                # the previous line should always render an exception
                self.assertEqual(True, False)
            except template.TemplateSyntaxError, e:
                self.assertEqual(e.args[0], 'Geotagging Error: This database does not support non-Point geometry distance lookups.')
        
class SyntaxTagTest(TestCase):
    
    def getNode(self, strng):
        from geotagging.templatetags.geotagging_tags import get_objects_nearby
        return get_objects_nearby(None, template.Token(template.TOKEN_BLOCK, 
                                                       strng))
        
    def assertNodeException(self, strng):
        self.assertRaises(template.TemplateSyntaxError, 
                          self.getNode, strng)

    def testInvalidSyntax(self):
        self.assertNodeException("get_objects_nearby as")
        self.assertNodeException("get_objects_nearby notas objects_nearby")
