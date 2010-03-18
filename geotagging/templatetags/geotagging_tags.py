from django import template
from django.conf import settings
from django.contrib.gis.measure import D
from django.db import models
from django.db.models import Q

from geotagging.models import Geotag, HAS_GEOGRAPHY

register = template.Library()

class GetGeotagsNode(template.Node):
    def __init__(self, geom, asvar=None, miles=5):
        self.geom = geom
        self.asvar = asvar
        self.distance = D(mi=miles)
        
    def render(self, context):
        try:
            geom = template.resolve_variable(self.geom, context)
        except template.VariableDoesNotExist:
            return ""
            
        # spheroid will result in more accurate results, but at the cost of
        # performance: http://code.djangoproject.com/ticket/6715
        if HAS_GEOGRAPHY:
            objects = Geotag.objects.filter(
                        Q(point__distance_lte=(geom, self.distance)) |
                        Q(line__distance_lte=(geom, self.distance)) |
                        Q(multilinestring__distance_lte=(geom, self.distance)) |
                        Q(polygon__distance_lte=(geom, self.distance)))
        else:
            if geom.geom_type != 'Point':
                raise template.TemplateSyntaxError("Geotagging Error: This database does not support non-Point geometry distance lookups.")
            else:
                objects = Geotag.objects.filter(point__distance_lte=(geom, 
                                                                 self.distance))
        context[self.asvar] = objects
        return ""

@register.tag
def get_objects_nearby(parser, token):
    """
    Populates a context variable with a list of :model:`geotagging.Geotag` objects
    that are within a given distance of a map geometry (point, line, polygon).
    Example::
    
        {% get_objects_nearby obj.point as nearby_objects %}
        
    This will find all objects tagged within 5 miles of ``obj.point``. To
    search within a different radius, use the following format::
        
        {% get_objects_nearby obj.point within 10 as nearby_objects %}
    
    This will find all objects tagged within 10 miles of ``obj.point``.
    
    *Note: Distances queries are approximate and may vary slightly from
    true measurements.*
    
    """
    
    bits = token.split_contents()
    item = bits[1]
    args = {}
    
    if len(bits) < 4:
        raise template.TemplateSyntaxError("%r tag takes at least 4 arguments" % bits[0])

    biter = iter(bits[2:])
    for bit in biter:
        if bit == "as":
            args["asvar"] = biter.next()
        elif bit == "within":
            args["miles"] = biter.next()
        else:
            raise template.TemplateSyntaxError("%r tag got an unknown argument: %r" % (bits[0], bit))
    
    return GetGeotagsNode(item, **args)
