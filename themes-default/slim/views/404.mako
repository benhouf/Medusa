<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        store,
        el: '#vue-wrap',
        metaInfo: {
            title: '404'
        },
        data() {
            return {
                header: 'Oops'
            };
        }
    });
};
</script>
</%block>
<%block name="content">
<h1 class="header">{{header}}</h1>
<div class="align-center">
You have reached this page by accident, please check the url.
</div>
</%block>
