'use strict';
window.TaxiApi = (() => {
  class ApiError extends Error { constructor(message,status=0,details=[]) {super(message);this.status=status;this.details=details;} }
  async function request(path,{method='GET',body,csrf='',token=''}={}) {
    const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),12000);
    try {
      const headers={'Content-Type':'application/json'};if(csrf)headers['X-Taxi-CSRF']=csrf;if(token)headers.Authorization=`Bearer ${token}`;
      const response=await fetch(path,{method,headers,credentials:'same-origin',cache:'no-store',signal:controller.signal,...(body===undefined?{}:{body:JSON.stringify(body)})});
      const data=response.status===204?null:await response.json();
      if(!response.ok) {
        const detail=data?.detail;
        const message=typeof detail==='string'?detail:Array.isArray(detail)?detail.map(e=>`${e.loc?.slice(1).join('.') || 'Field'}: ${e.msg}`).join(' · '):`Request rejected (HTTP ${response.status}).`;
        throw new ApiError(message,response.status,Array.isArray(detail)?detail:[]);
      }
      return data;
    } catch(error) {
      if(error instanceof ApiError)throw error;
      throw new ApiError(error.name==='AbortError'?'Request timed out. Result is unconfirmed; refresh before retrying.':'Disconnected from the server. Check the connection and retry.');
    } finally {clearTimeout(timer);}
  }
  function showError(error,id,form) {
    Taxi.message(id,error.message,true);
    for(const item of error.details || []) {
      const field=item.loc?.[1];if(!field || !form)continue;
      const input=form.querySelector(`[name="${CSS.escape(field)}"]`);if(input)input.setAttribute('aria-invalid','true');
    }
  }
  return {request,showError,ApiError};
})();
