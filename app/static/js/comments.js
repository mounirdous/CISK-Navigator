/**
 * Comments & Collaboration Module
 *
 * Handles cell comments, @mentions, and threaded discussions
 */

class CommentsManager {
    constructor() {
        this.currentConfigId = null;
        this.comments = [];
        this.users = [];  // For @mention autocomplete
    }

    /**
     * Open comment modal for a KPI cell
     */
    openCommentModal(configId, kpiName, valueTypeName) {
        this.currentConfigId = configId;

        // Update modal title
        document.getElementById('commentModalTitle').textContent =
            `Comments: ${kpiName} - ${valueTypeName}`;

        // Load comments
        this.loadComments(configId);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('commentModal'));
        modal.show();
    }

    /**
     * Load all comments for a cell
     */
    async loadComments(configId) {
        try {
            const response = await fetch(`/workspace/api/cell/${configId}/comments`);
            const data = await response.json();

            if (response.ok) {
                this.comments = data.rendered_comments || [];
                this.renderComments();
                this.updateCommentCount(configId, data.count);
            } else {
                console.error('Failed to load comments:', data.error);
            }
        } catch (error) {
            console.error('Error loading comments:', error);
        }
    }

    /**
     * Render comments in the modal
     */
    renderComments() {
        const container = document.getElementById('commentsContainer');

        if (this.comments.length === 0) {
            container.innerHTML = '<p class="text-muted">No comments yet. Be the first to comment!</p>';
            return;
        }

        container.innerHTML = this.comments.map(comment => this.renderComment(comment, 0)).join('');

        // Add event listeners for actions
        this.attachCommentListeners();
    }

    /**
     * Render a single comment with its replies
     */
    renderComment(comment, depth = 0) {
        const isResolved = comment.is_resolved ? 'resolved' : '';
        const resolveBtn = comment.is_resolved
            ? `<button class="btn btn-sm btn-outline-success unresolve-btn" data-id="${comment.id}">Unresolve</button>`
            : `<button class="btn btn-sm btn-outline-secondary resolve-btn" data-id="${comment.id}">Resolve</button>`;

        const indent = depth * 20;  // 20px per level
        const replyCount = comment.replies && comment.replies.length > 0
            ? `<small class="text-muted">${comment.replies.length} ${comment.replies.length === 1 ? 'reply' : 'replies'}</small>`
            : '';

        let html = `
            <div class="comment-item ${isResolved}" data-comment-id="${comment.id}" style="margin-left: ${indent}px;">
                <div class="comment-header">
                    <strong>${comment.user_name}</strong>
                    <small class="text-muted">${this.formatDate(comment.created_at)}</small>
                    ${comment.is_resolved ? '<span class="badge bg-success">Resolved</span>' : ''}
                </div>
                <div class="comment-body">
                    ${comment.rendered_text}
                </div>
                <div class="comment-actions">
                    <button class="btn btn-sm btn-link reply-btn" data-id="${comment.id}">Reply</button>
                    ${depth === 0 ? resolveBtn : ''}
                    <button class="btn btn-sm btn-link text-danger delete-btn" data-id="${comment.id}">Delete</button>
                    ${replyCount}
                </div>
                <div class="comment-replies" id="replies-${comment.id}"></div>
            </div>
        `;

        // Render replies recursively
        if (comment.replies && comment.replies.length > 0) {
            for (const reply of comment.replies) {
                html += this.renderComment(reply, depth + 1);
            }
        }

        return html;
    }

    /**
     * Attach event listeners to comment actions
     */
    attachCommentListeners() {
        // Reply buttons
        document.querySelectorAll('.reply-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const commentId = e.target.dataset.id;
                this.showReplyForm(commentId);
            });
        });

        // Resolve buttons
        document.querySelectorAll('.resolve-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const commentId = e.target.dataset.id;
                this.resolveComment(commentId);
            });
        });

        // Unresolve buttons
        document.querySelectorAll('.unresolve-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const commentId = e.target.dataset.id;
                this.unresolveComment(commentId);
            });
        });

        // Delete buttons
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const commentId = e.target.dataset.id;
                if (confirm('Delete this comment? This action cannot be undone.')) {
                    this.deleteComment(commentId);
                }
            });
        });
    }

    /**
     * Post a new comment
     */
    async postComment() {
        const textarea = document.getElementById('newCommentText');
        const commentText = textarea.value.trim();

        if (!commentText) {
            alert('Please enter a comment');
            return;
        }

        try {
            const response = await fetch(`/workspace/api/cell/${this.currentConfigId}/comments`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ comment_text: commentText })
            });

            const data = await response.json();

            if (response.ok) {
                textarea.value = '';  // Clear form
                this.loadComments(this.currentConfigId);  // Reload
            } else {
                alert('Error posting comment: ' + data.error);
            }
        } catch (error) {
            console.error('Error posting comment:', error);
            alert('Error posting comment');
        }
    }

    /**
     * Delete a comment
     */
    async deleteComment(commentId) {
        try {
            const response = await fetch(`/workspace/api/comments/${commentId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.loadComments(this.currentConfigId);
            } else {
                const data = await response.json();
                alert('Error deleting comment: ' + data.error);
            }
        } catch (error) {
            console.error('Error deleting comment:', error);
        }
    }

    /**
     * Resolve a comment
     */
    async resolveComment(commentId) {
        try {
            const response = await fetch(`/workspace/api/comments/${commentId}/resolve`, {
                method: 'POST'
            });

            if (response.ok) {
                this.loadComments(this.currentConfigId);
            } else {
                const data = await response.json();
                alert('Error resolving comment: ' + data.error);
            }
        } catch (error) {
            console.error('Error resolving comment:', error);
        }
    }

    /**
     * Unresolve a comment
     */
    async unresolveComment(commentId) {
        try {
            const response = await fetch(`/workspace/api/comments/${commentId}/unresolve`, {
                method: 'POST'
            });

            if (response.ok) {
                this.loadComments(this.currentConfigId);
            } else {
                const data = await response.json();
                alert('Error unresolving comment: ' + data.error);
            }
        } catch (error) {
            console.error('Error unresolving comment:', error);
        }
    }

    /**
     * Show reply form
     */
    showReplyForm(parentCommentId) {
        // Hide any existing reply forms
        document.querySelectorAll('.reply-form-container').forEach(form => form.remove());

        const repliesContainer = document.getElementById(`replies-${parentCommentId}`);
        if (!repliesContainer) return;

        // Create reply form
        const replyForm = document.createElement('div');
        replyForm.className = 'reply-form-container mt-2 p-2 border rounded';
        replyForm.innerHTML = `
            <textarea class="form-control form-control-sm" id="reply-text-${parentCommentId}"
                      rows="2" placeholder="Write a reply..."></textarea>
            <div class="mt-2">
                <button class="btn btn-sm btn-primary" onclick="commentsManager.submitReply(${parentCommentId})">Reply</button>
                <button class="btn btn-sm btn-secondary" onclick="this.closest('.reply-form-container').remove()">Cancel</button>
            </div>
        `;

        repliesContainer.appendChild(replyForm);

        // Focus textarea
        document.getElementById(`reply-text-${parentCommentId}`).focus();

        // Setup mention autocomplete on reply textarea
        const textarea = document.getElementById(`reply-text-${parentCommentId}`);
        this.setupMentionAutocomplete(textarea);
    }

    /**
     * Submit a reply
     */
    async submitReply(parentCommentId) {
        const textarea = document.getElementById(`reply-text-${parentCommentId}`);
        const commentText = textarea.value.trim();

        if (!commentText) {
            alert('Please enter a reply');
            return;
        }

        try {
            const response = await fetch(`/workspace/api/cell/${this.currentConfigId}/comments`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    comment_text: commentText,
                    parent_comment_id: parentCommentId
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.loadComments(this.currentConfigId);  // Reload all
            } else {
                alert('Error posting reply: ' + data.error);
            }
        } catch (error) {
            console.error('Error posting reply:', error);
            alert('Error posting reply');
        }
    }

    /**
     * Setup @mention autocomplete
     */
    setupMentionAutocomplete(textarea) {
        let mentionTimeout;
        let currentDropdown = null;
        let selectedIndex = -1;

        textarea.addEventListener('input', (e) => {
            const text = e.target.value;
            const cursorPos = e.target.selectionStart;

            // Find last @ before cursor
            const textBeforeCursor = text.substring(0, cursorPos);
            const lastAtIndex = textBeforeCursor.lastIndexOf('@');

            if (lastAtIndex !== -1) {
                const searchTerm = textBeforeCursor.substring(lastAtIndex + 1);

                // Search if we have 0+ characters and no spaces (show all users after just @)
                if (!searchTerm.includes(' ')) {
                    clearTimeout(mentionTimeout);
                    mentionTimeout = setTimeout(() => {
                        this.searchUsers(searchTerm, textarea, lastAtIndex);
                    }, 200);  // Faster response
                } else {
                    this.hideMentionDropdown();
                }
            } else {
                this.hideMentionDropdown();
            }
        });

        // Keyboard navigation
        textarea.addEventListener('keydown', (e) => {
            const dropdown = document.getElementById('mentionDropdown');
            if (!dropdown || dropdown.style.display === 'none') return;

            const items = dropdown.querySelectorAll('.mention-item');
            if (items.length === 0) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                this.highlightDropdownItem(items, selectedIndex);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                this.highlightDropdownItem(items, selectedIndex);
            } else if (e.key === 'Enter' && selectedIndex >= 0) {
                e.preventDefault();
                items[selectedIndex].click();
                selectedIndex = -1;
            } else if (e.key === 'Escape') {
                this.hideMentionDropdown();
                selectedIndex = -1;
            }
        });
    }

    /**
     * Highlight selected item in dropdown
     */
    highlightDropdownItem(items, index) {
        items.forEach((item, i) => {
            if (i === index) {
                item.style.background = '#e7f3ff';
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.style.background = '';
            }
        });
    }

    /**
     * Search users for @mention
     */
    async searchUsers(searchTerm, textarea, atIndex) {
        try {
            const response = await fetch(`/workspace/api/org/users/search?q=${encodeURIComponent(searchTerm)}`);
            const data = await response.json();

            if (response.ok && data.users.length > 0) {
                this.showMentionDropdown(data.users, textarea, atIndex);
            } else {
                this.hideMentionDropdown();
            }
        } catch (error) {
            console.error('Error searching users:', error);
        }
    }

    /**
     * Show mention dropdown
     */
    showMentionDropdown(users, textarea, atIndex) {
        let dropdown = document.getElementById('mentionDropdown');

        if (!dropdown) {
            dropdown = document.createElement('div');
            dropdown.id = 'mentionDropdown';
            dropdown.className = 'mention-dropdown';
            document.body.appendChild(dropdown);
        }

        if (users.length === 0) {
            dropdown.innerHTML = '<div class="mention-item text-muted">No users found</div>';
        } else {
            dropdown.innerHTML = users.map(user => `
                <div class="mention-item" data-login="${user.login}" data-name="${user.display_name}">
                    <strong>${user.display_name}</strong> <small class="text-muted">@${user.login}</small>
                </div>
            `).join('');
        }

        // Position dropdown below textarea (with better calculation)
        const rect = textarea.getBoundingClientRect();
        dropdown.style.top = (rect.bottom + window.scrollY + 2) + 'px';
        dropdown.style.left = (rect.left + window.scrollX) + 'px';
        dropdown.style.width = Math.max(rect.width, 250) + 'px';
        dropdown.style.display = 'block';

        // Add click handlers
        dropdown.querySelectorAll('.mention-item[data-login]').forEach(item => {
            item.addEventListener('click', () => {
                const login = item.dataset.login;
                const text = textarea.value;
                const cursorPos = textarea.selectionStart;
                const textBeforeCursor = text.substring(0, cursorPos);
                const searchStart = textBeforeCursor.lastIndexOf('@');

                if (searchStart !== -1) {
                    const newText = text.substring(0, searchStart) + `@${login} ` + text.substring(cursorPos);
                    textarea.value = newText;
                    // Position cursor after the mention
                    const newCursorPos = searchStart + login.length + 2;
                    textarea.setSelectionRange(newCursorPos, newCursorPos);
                }

                this.hideMentionDropdown();
                textarea.focus();
            });
        });
    }

    /**
     * Hide mention dropdown
     */
    hideMentionDropdown() {
        const dropdown = document.getElementById('mentionDropdown');
        if (dropdown) {
            dropdown.style.display = 'none';
        }
    }

    /**
     * Update comment count badge on cell
     */
    updateCommentCount(configId, count) {
        const badge = document.querySelector(`[data-config-id="${configId}"] .comment-count`);
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
        }
    }

    /**
     * Format date for display
     */
    formatDate(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
        if (diffMins < 10080) return `${Math.floor(diffMins / 1440)}d ago`;

        return date.toLocaleDateString();
    }
}

// Initialize
const commentsManager = new CommentsManager();

// Setup when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Setup mention autocomplete on comment textarea
    const commentTextarea = document.getElementById('newCommentText');
    if (commentTextarea) {
        commentsManager.setupMentionAutocomplete(commentTextarea);
    }

    // Post comment button
    const postBtn = document.getElementById('postCommentBtn');
    if (postBtn) {
        postBtn.addEventListener('click', () => {
            commentsManager.postComment();
        });
    }

    // Load unread mentions count
    loadUnreadMentionsCount();
});

/**
 * Load unread mentions count for notification badge
 */
async function loadUnreadMentionsCount() {
    try {
        const response = await fetch('/workspace/api/mentions/unread?limit=1');
        const data = await response.json();

        if (response.ok) {
            updateMentionsBadge(data.count);
        }
    } catch (error) {
        console.error('Error loading mentions count:', error);
    }
}

/**
 * Update mentions notification badge
 */
function updateMentionsBadge(count) {
    const badge = document.getElementById('mentionsBadge');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-block' : 'none';
    }
}
