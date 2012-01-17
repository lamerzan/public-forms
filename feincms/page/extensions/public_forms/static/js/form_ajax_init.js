var ajax_init = function(container_id){
    var formwrapper = $(container_id + '_public_form')
    var forms = formwrapper.getChildren('form').each(function(form, index, array){
        form_ajax_init(form, formwrapper)
    })
}
var form_ajax_init = function(form, formwrapper){
  var ajax = new Form.Request(form, formwrapper, {
      requestOptions:{evalScripts:true}
  });
  ajax.addEvents({
              send:function(form, data){
                  formwrapper.addClass('ajax-form-send')
                  formwrapper.removeClass('ajax-form-success')
                  formwrapper.removeClass('ajax-form-failure')
                  },
              success:function(target, text, xml){
                  formwrapper.removeClass('ajax-form-send')
                  formwrapper.addClass('ajax-form-success')
                  },
              failure:function(xhr){
                  formwrapper.removeClass('ajax-form-send')
                  formwrapper.addClass('ajax-form-failure')
                  }
            })
}