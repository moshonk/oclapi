from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from concepts.models import Concept
from oclapi.models import BaseModel
from oclapi.utils import reverse_resource
from sources.models import Source

MAPPING_RESOURCE_TYPE = 'Mapping'


class Mapping(BaseModel):
    parent = models.ForeignKey(Source, related_name='mappings_from')
    map_type = models.TextField()
    from_concept = models.ForeignKey(Concept, related_name='mappings_from')
    to_concept = models.ForeignKey(Concept, null=True, blank=True, related_name='mappings_to')
    to_source = models.ForeignKey(Source, null=True, blank=True, related_name='mappings_to')
    to_concept_code = models.TextField(null=True, blank=True)
    to_concept_name = models.TextField(null=True, blank=True)
    retired = models.BooleanField(default=False)
    external_id = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = (
            ("parent", "map_type", "from_concept", "to_concept"),
            ("parent", "map_type", "from_concept", "to_source", "to_concept_code", "to_concept_name")
        )

    def clean(self, exclude=None):
        messages = []
        try:
            self.from_concept
        except Concept.DoesNotExist:
            messages.append("Must specify a 'from_concept'.")
        if not self.to_concept or (self.to_source and self.to_concept_code and self.to_concept_name):
            messages.append("Must specify either 'to_concept' or 'to_source', 'to_concept_code' & 'to_concept_name'")
        if self.to_concept and (self.to_source or self.to_concept_name or self.to_concept_code):
            messages.append("Must specify one of 'to_concept' or 'to_source', 'to_concept_name' & 'to_concept_code'.  Cannot specify both.")
        if messages:
            raise ValidationError(' '.join(messages))

    @property
    def from_source(self):
        return self.from_concept.parent

    @property
    def from_source_owner(self):
        return self.from_source.owner_name

    @property
    def from_source_name(self):
        return self.from_source.mnemonic

    @property
    def from_source_url(self):
        return reverse_resource(self.from_source, 'source-detail')

    @property
    def from_source_shorthand(self):
        return "%s:%s" % (self.from_source_owner, self.from_source_name)

    @property
    def from_concept_code(self):
        return self.from_concept.mnemonic

    @property
    def from_concept_url(self):
        return reverse_resource(self.from_concept, 'concept-detail')

    @property
    def from_concept_shorthand(self):
        return "%s:%s" % (self.from_source_shorthand, self.from_concept_code)

    def get_to_source(self):
        return self.to_source or self.to_concept.parent

    @property
    def to_source_name(self):
        return self.get_to_source().mnemonic

    def get_to_source_url(self):
        return reverse_resource(self.get_to_source(), 'source-detail')

    @property
    def to_source_owner(self):
        return unicode(self.get_to_source().parent)

    @property
    def to_source_shorthand(self):
        return "%s:%s" % (self.to_source_owner, self.to_source_name)

    def get_to_concept_name(self):
        return self.to_concept_name or self.to_concept.display_name

    def get_to_concept_code(self):
        return self.to_concept_code or self.to_concept.mnemonic

    def to_concept_shorthand(self):
        return "%s:%s" % (self.to_source_shorthand, self.to_concept_code)

    @staticmethod
    def resource_type():
        return MAPPING_RESOURCE_TYPE

    @staticmethod
    def get_url_kwarg():
        return 'mapping'

    @classmethod
    def persist_changes(cls, obj, updated_by, **kwargs):
        created = kwargs.pop('created', False)
        errors = dict()
        try:
            obj.updated_by = updated_by
            obj.full_clean()
        except ValidationError as e:
            errors.update(e.message_dict)
            return errors

        persisted = False
        try:
            obj.updated_by = updated_by
            obj.save(**kwargs)
            if created:
                obj.mnemonic = obj.id
                obj.save(**kwargs)

            persisted = True
        finally:
            if not persisted:
                errors['non_field_errors'] = ["Failed to persist mapping."]
        return errors

    @classmethod
    def persist_new(cls, obj, updated_by, **kwargs):
        errors = dict()
        non_field_errors = []
        owner = kwargs.pop('owner', None)
        if owner is None:
            non_field_errors.append('Must specify an owner')
        obj.owner = owner
        obj.updated_by = owner
        parent_resource = kwargs.pop('parent_resource', None)
        if parent_resource is None:
            non_field_errors.append('Must specify a parent source')
        obj.parent = parent_resource
        obj.public_access = parent_resource.public_access
        if non_field_errors:
            errors['non_field_errors'] = non_field_errors
            return errors
        obj.mnemonic = 'TEMP'
        kwargs.update({'created': True})
        return cls.persist_changes(obj, updated_by, **kwargs)


@receiver(post_save, sender=Source)
def propagate_parent_attributes(sender, instance=None, created=False, **kwargs):
    if created:
        return
    for mapping in Mapping.objects.filter(parent_id=instance.id):
        update_index = False
        if mapping.is_active != instance.is_active:
            update_index = True
            mapping.is_active = instance.is_active
        if mapping.public_access != instance.public_access:
            update_index |= True
            mapping.public_access = instance.public_access
        if update_index:
            mapping.save()


@receiver(post_save, sender=Source)
def propagate_owner_status(sender, instance=None, created=False, **kwargs):
    if created:
        return
    for mapping in Mapping.objects.filter(parent_id=instance.id):
        if (instance.is_active and not mapping.is_active) or (mapping.is_active and not instance.is_active):
            mapping.save()
