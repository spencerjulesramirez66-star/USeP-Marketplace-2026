/* Shared seller helpers: modal, select options, file queue, gallery tile, stock editor. */

/* ===== modal ===== */
/* Modal open/close. Markup contract:
   <button data-open-modal="modal-id"> and <button data-close-modal="modal-id">. */
(function (Seller) {
    Seller.modal = {
        open(modal) { if (modal) modal.hidden = false; },
        close(modal) { if (modal) modal.hidden = true; },
    };

    document.addEventListener('click', (event) => {
        const opener = event.target.closest('[data-open-modal]');
        if (opener) Seller.modal.open(document.getElementById(opener.dataset.openModal));

        const closer = event.target.closest('[data-close-modal]');
        if (closer) Seller.modal.close(document.getElementById(closer.dataset.closeModal));
    });
})(window.Seller = window.Seller || {});

/* ===== select-options ===== */
/* Read a <select>'s options into plain objects, and re-render a filtered subset. */
(function (Seller) {
    Seller.options = {
        read(select) {
            return Array.from(select.querySelectorAll('option')).map((option) => ({
                value: option.value,
                label: option.textContent,
                slug: option.dataset.slug || null,
                type: option.dataset.type || null,
            }));
        },

        render(select, items, placeholder) {
            select.innerHTML = '';
            if (placeholder) {
                const hint = document.createElement('option');
                hint.value = '';
                hint.textContent = placeholder;
                hint.disabled = true;
                hint.selected = true;
                select.appendChild(hint);
            }
            items.forEach((item) => {
                const option = document.createElement('option');
                option.value = item.value;
                option.textContent = item.label;
                if (item.slug) option.dataset.slug = item.slug;
                if (item.type) option.dataset.type = item.type;
                select.appendChild(option);
            });
        },
    };
})(window.Seller = window.Seller || {});

/* ===== file-queue ===== */
/* Keeps a file <input multiple> in sync with an accumulating list of files,
   so photos can be added in several picks and removed one by one.

   const queue = Seller.fileQueue(input, { limit: 8, onChange: (files) => render(files) });
   queue.add(input.files); queue.remove(file); queue.clear(); queue.files */
(function (Seller) {
    Seller.fileQueue = function (input, { limit = Infinity, onChange = () => {} } = {}) {
        let files = [];

        function commit() {
            const transfer = new DataTransfer();
            files.forEach((file) => transfer.items.add(file));
            input.files = transfer.files;
            onChange(files);
        }

        return {
            get files() { return files; },
            add(incoming) {
                files = [...files, ...Array.from(incoming)].slice(0, limit);
                commit();
            },
            remove(file) {
                files = files.filter((item) => item !== file);
                commit();
            },
            clear() {
                files = [];
                commit();
            },
        };
    };
})(window.Seller = window.Seller || {});

/* ===== gallery-tile ===== */
/* Builds one thumbnail tile (image + trash button) for the photo galleries.

   const { item, img, remove } = Seller.gallery.tile({
       url, alt, label, active, pending, data, onSelect, onRemove,
   });
   `data` becomes data-* attributes on the remove button. */
(function (Seller) {
    Seller.gallery = {
        tile({ url, alt, label = '', active = false, pending = false, data = {}, onSelect, onRemove }) {
            const item = document.createElement('div');
            item.className = 'manage-gallery-item' + (pending ? ' pending-gallery-item' : '');

            const img = document.createElement('img');
            img.className = 'manage-gallery-image' + (active ? ' active' : '');
            img.src = url;
            img.alt = alt;
            if (onSelect) img.addEventListener('click', () => onSelect(img, url));
            item.appendChild(img);

            if (label) {
                const tag = document.createElement('span');
                tag.className = 'photo-tile-label';
                tag.textContent = label;
                item.appendChild(tag);
            }

            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'remove-gallery-image';
            remove.title = 'Remove photo';
            remove.setAttribute('aria-label', 'Remove photo');
            remove.innerHTML = '<i class="bi bi-trash3" aria-hidden="true"></i>';
            Object.entries(data).forEach(([key, value]) => { remove.dataset[key] = value; });
            remove.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                if (onRemove) onRemove(item);
                item.remove();
            });
            item.appendChild(remove);

            return { item, img, remove };
        },

        /* Mark one thumbnail as the selected/main one within its gallery. */
        activate(container, img) {
            container.querySelectorAll('.manage-gallery-image').forEach((entry) => entry.classList.remove('active'));
            img.classList.add('active');
        },
    };
})(window.Seller = window.Seller || {});

/* ===== stock-editor ===== */
/* Stock quantity editor, shared by the Add modal, Manage modal, and Edit page.

   Markup contract (see stock_editor.html):
   <div class="stock-editor" data-category-select="#category-select-id"> ... </div>

   - +/- buttons step the number input (never below 0).
   - When the linked category is "Services" the editor hides and stock is 0;
     switching back to a product category restores the previous value. */
(function (Seller) {
    const input = (editor) => editor.querySelector('input[type="number"]');

    function sync(editor, { fresh = false } = {}) {
        const select = document.querySelector(editor.dataset.categorySelect);
        const stock = input(editor);
        if (!select || !stock) return;

        const isService = select.selectedOptions[0]?.dataset.slug === 'services';
        const previous = fresh ? null : editor.dataset.mode;

        editor.hidden = isService;
        editor.dataset.mode = isService ? 'service' : 'product';

        if (isService && previous !== 'service') {
            if (stock.value !== '0') editor.dataset.lastValue = stock.value;
            stock.value = '0';
        } else if (!isService && previous === 'service') {
            stock.value = editor.dataset.lastValue || '1';
        }
    }

    function bind(editor) {
        const select = document.querySelector(editor.dataset.categorySelect);
        if (select) select.addEventListener('change', () => sync(editor));

        editor.addEventListener('click', (event) => {
            const button = event.target.closest('.stepper-button');
            const stock = input(editor);
            if (!button || !stock) return;
            stock.value = Math.max(0, Number(stock.value || 0) + Number(button.dataset.step || 1));
        });

        sync(editor, { fresh: true });
    }

    /* `fresh: true` re-reads the category without treating it as a user switch
       (used when the Manage modal is filled from a listing card). */
    Seller.stockEditor = { sync };

    document.querySelectorAll('.stock-editor[data-category-select]').forEach(bind);
})(window.Seller = window.Seller || {});
