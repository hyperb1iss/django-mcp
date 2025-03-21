from django.db import models


class TestPost(models.Model):
    """A simple test model for a blog post."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = "post"
        verbose_name_plural = "posts"


class TestComment(models.Model):
    """A simple test model for a blog comment."""

    post = models.ForeignKey(TestPost, on_delete=models.CASCADE, related_name="comments")
    author = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.post.title}"

    class Meta:
        verbose_name = "comment"
        verbose_name_plural = "comments"
