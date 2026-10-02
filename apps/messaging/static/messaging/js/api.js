// Centralized API access: CSRF, headers, JSON parsing, error handling.
// Higher-level modules call the functions below instead of touching fetch().

function getCsrfToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
}

export class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.status = status;
    }
}

async function handle(response) {
    let data = null;
    try {
        data = await response.json();
    } catch {
        // Some endpoints (e.g. a redirect from a non-AJAX form post) may not return JSON.
    }
    if (!response.ok) {
        throw new ApiError(data && data.error ? data.error : `Request failed (${response.status})`, response.status);
    }
    return data;
}

export function get(url, { signal } = {}) {
    return fetch(url, {
        method: 'GET',
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        signal,
    }).then(handle);
}

export function postForm(url, formData, { signal } = {}) {
    formData.append('csrfmiddlewaretoken', getCsrfToken());
    return fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest', Accept: 'application/json' },
        body: formData,
        signal,
    }).then(handle);
}

/** Same as postForm, but reports upload progress (fetch cannot). */
export function postFormWithProgress(url, formData, onProgress) {
    formData.append('csrfmiddlewaretoken', getCsrfToken());
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', url);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.responseType = 'json';
        if (xhr.upload && onProgress) {
            xhr.upload.onprogress = (evt) => {
                if (evt.lengthComputable) onProgress(evt.loaded / evt.total);
            };
        }
        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(xhr.response);
            } else {
                reject(new ApiError((xhr.response && xhr.response.error) || `Request failed (${xhr.status})`, xhr.status));
            }
        };
        xhr.onerror = () => reject(new ApiError('Network error.', 0));
        xhr.send(formData);
    });
}
