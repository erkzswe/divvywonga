from django.contrib import admin
from users.models import Group, Membership


class MembershipInline(admin.TabularInline):
    """Inline admin for Membership model to show in Group admin."""
    model = Membership
    extra = 1
    fields = ('user', 'points', 'role', 'is_active')
    readonly_fields = ('joined_at',)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """Admin configuration for Group model."""
    list_display = ('name', 'is_active', 'member_count', 'total_points', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MembershipInline]
    
    def member_count(self, obj):
        """Display number of active members."""
        return obj.get_active_members().count()
    member_count.short_description = 'Active Members'
    
    def total_points(self, obj):
        """Display total points for the group."""
        return obj.get_total_points()
    total_points.short_description = 'Total Points'


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Admin configuration for Membership model."""
    list_display = ('user', 'group', 'points', 'role', 'is_active', 'joined_at')
    list_filter = ('role', 'is_active', 'joined_at', 'group')
    search_fields = ('user__username', 'user__email', 'group__name')
    readonly_fields = ('joined_at',)
    
    fieldsets = (
        ('Relationship', {
            'fields': ('user', 'group')
        }),
        ('Membership Details', {
            'fields': ('points', 'role', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('joined_at',),
            'classes': ('collapse',)
        })
    )
