from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField, HnswIndex

class Source(models.Model):
    KIND_CHOICES = [
        ('TEXT', 'Text'),
        ('FILE', 'File'),
        ('GITHUB', 'GitHub'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('READY', 'Ready'),
        ('FAILED', 'Failed'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sources')
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    origin_url = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(null=True, blank=True)
    file_count = models.IntegerField(default=0)
    chunk_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.kind} - {self.status})"


class SourceFile(models.Model):
    KIND_CHOICES = [
        ('DOCUMENT', 'Document'),
        ('CODE', 'Code'),
    ]
    STATUS_CHOICES = [
        ('READY', 'Ready'),
        ('SKIPPED', 'Skipped'),
        ('FAILED', 'Failed'),
    ]

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='files')
    path = models.CharField(max_length=500)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    language = models.CharField(max_length=50, null=True, blank=True)
    topic = models.CharField(max_length=255, null=True, blank=True)
    page_count = models.IntegerField(null=True, blank=True)
    extracted_text = models.TextField(null=True, blank=True)
    size_bytes = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    skip_reason = models.CharField(max_length=255, null=True, blank=True)
    chunk_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['path']

    def __str__(self):
        return f"{self.path} ({self.status})"


class Chunk(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='chunks')
    source_file = models.ForeignKey(SourceFile, on_delete=models.CASCADE, related_name='chunks')
    position = models.IntegerField()
    text = models.TextField()
    page_number = models.IntegerField(null=True, blank=True)
    start_line = models.IntegerField(null=True, blank=True)
    end_line = models.IntegerField(null=True, blank=True)
    embedding = VectorField(dimensions=384)

    class Meta:
        ordering = ['position']
        indexes = [
            HnswIndex(
                name='chunk_embedding_hnsw_idx',
                fields=['embedding'],
                opclasses=['vector_cosine_ops'],
            )
        ]

    def __str__(self):
        return f"Chunk {self.position} of {self.source_file.path}"


class Question(models.Model):
    EVIDENCE_CHOICES = [
        ('SUFFICIENT', 'Sufficient'),
        ('INSUFFICIENT', 'Insufficient'),
        ('NO_SOURCES', 'No Sources'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='questions')
    code = models.TextField(max_length=20000, blank=True, default='')
    language = models.CharField(max_length=50, null=True, blank=True)
    question_text = models.TextField(max_length=2000, blank=True, default='')
    source_ids = models.JSONField(default=list)
    answer = models.JSONField(default=dict)
    evidence_status = models.CharField(max_length=20, choices=EVIDENCE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Question {self.id} ({self.evidence_status}) by {self.owner.username}"


class RetrievedChunk(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='retrieved_chunks')
    chunk = models.ForeignKey(Chunk, null=True, blank=True, on_delete=models.SET_NULL, related_name='retrievals')
    rank = models.IntegerField()
    score = models.FloatField()
    saved_label = models.TextField(blank=True, default='')
    saved_text = models.TextField(blank=True, default='')
    cited = models.BooleanField(default=False)

    class Meta:
        ordering = ['rank']

    def __str__(self):
        return f"RetrievedChunk rank {self.rank} for Q{self.question_id}"
