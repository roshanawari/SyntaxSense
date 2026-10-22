from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from kb.models import Source, SourceFile, Chunk
from kb.rag.retrieval import embed_texts

class Command(BaseCommand):
    help = 'Seeds one demo user and one small TEXT source with real chunks and embeddings.'

    def handle(self, *args, **options):
        email = 'demo@example.com'
        password = settings.SEED_PASSWORD

        # Create or update demo user
        user, created = User.objects.get_or_create(username=email, defaults={'email': email})
        user.email = email
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created demo user: {email}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated password for demo user: {email}"))

        # Clean up any existing seeded source for repeatability
        Source.objects.filter(owner=user, name='Python Quick Reference').delete()

        # Seed content
        chunk1_text = (
            "Python Dictionaries and KeyErrors:\n"
            "A dictionary in Python maps hashable keys to arbitrary values. Accessing a non-existent key "
            "using bracket notation `d[key]` raises a KeyError. To safely retrieve values with a fallback, "
            "use `d.get(key, default)`. Alternatively, use collections.defaultdict to assign default factories."
        )

        chunk2_text = (
            "Python List Comprehensions and Exceptions:\n"
            "List comprehensions provide a concise way to create lists: `[f(x) for x in iterable if condition]`. "
            "When performing division or parsing within a comprehension, handle ZeroDivisionError or ValueError "
            "either by filtering beforehand or using helper functions with try-except blocks."
        )

        source_text = f"{chunk1_text}\n\n{chunk2_text}"

        source = Source.objects.create(
            owner=user,
            name='Python Quick Reference',
            kind='TEXT',
            status='READY',
            file_count=1,
            chunk_count=2,
        )

        source_file = SourceFile.objects.create(
            source=source,
            path='python_quick_reference.txt',
            kind='DOCUMENT',
            topic='Python Dictionaries & Comprehensions',
            size_bytes=len(source_text.encode('utf-8')),
            extracted_text=source_text,
            status='READY',
            chunk_count=2,
        )

        self.stdout.write("Computing real embeddings via sentence-transformers...")
        embeddings = embed_texts([chunk1_text, chunk2_text])

        Chunk.objects.create(
            source=source,
            source_file=source_file,
            position=1,
            text=chunk1_text,
            embedding=embeddings[0],
        )

        Chunk.objects.create(
            source=source,
            source_file=source_file,
            position=2,
            text=chunk2_text,
            embedding=embeddings[1],
        )

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded source '{source.name}' (ID {source.id}) with 2 chunks and real embeddings for {email}."
        ))
