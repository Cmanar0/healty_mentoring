from django.db import models

class Qualification(models.Model):
    """Qualifications model for mentors"""
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    description = models.TextField(max_length=450, blank=True)

    class Meta:
        verbose_name = "Qualification"
        verbose_name_plural = "Qualifications"
        ordering = ['title']

    def __str__(self):
        return self.title

class MentorProfileQualification(models.Model):
    """Through model for MentorProfile-Qualification relationship with order"""
    mentor_profile = models.ForeignKey("accounts.MentorProfile", on_delete=models.CASCADE)
    qualification = models.ForeignKey("Qualification", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'qualification__title']
        unique_together = ['mentor_profile', 'qualification']

    def __str__(self):
        return f"{self.mentor_profile} - {self.qualification} (order: {self.order})"

class Tag(models.Model):
    """Tags for filtering mentors"""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['name']

    def __str__(self):
        return self.name
