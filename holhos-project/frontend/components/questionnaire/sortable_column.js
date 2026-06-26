import 'https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.3/Sortable.min.js'

export default {
    template: `
        <div>
            <slot></slot>
        </div>
    `,
    props: {
        group: String,
    },
    mounted() {
        this.makeSortable();
    },
    methods: {
        makeSortable() {
            const group = this.group === 'None' ? this.$el.id : this.group;
            Sortable.create(this.$el, {
                group: group,
                animation: 150,
                handle: ".drag-handle",
                ghostClass: 'opacity-50',
                onEnd: (evt) => {
                    this.$emit("item-drop", {
                        parent: parseInt(this.$el.id.slice(1)),
                        id: parseInt(evt.item.id.slice(1)),
                        new_index: evt.newIndex,
                        old_index: evt.oldIndex,
                    });
                },
            });
        },
    },
};
