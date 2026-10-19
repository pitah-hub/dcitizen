from django.contrib import admin

from .models import Category, Comment, County, Feedback, ServiceRequest, StatusUpdate


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "is_active")


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class StatusUpdateInline(admin.TabularInline):
    model = StatusUpdate
    extra = 0
    can_delete = False
    readonly_fields = ("old_status", "new_status", "changed_by", "note", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("reference", "category", "county", "status", "user", "created_at")
    list_filter = ("status", "category", "county")
    search_fields = ("reference", "user__email", "user__full_name", "area")
    # status is read-only here on purpose: it must change through change_status().
    readonly_fields = ("reference", "status", "created_at", "updated_at")
    inlines = [StatusUpdateInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("request", "author", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("request", "rating", "created_at")
    readonly_fields = ("created_at",)