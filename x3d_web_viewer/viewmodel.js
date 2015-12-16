/*
FILE NAME  : viewmodel.js
DESCRIPTION: x3d viewer
REVISION: 1.00
AUTHOR: Oleg Dzhimiev <oleg@elphel.com>
Copyright (C) 2015 Elphel, Inc.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>
*/

var model = "Undefined";
var NSN = "m";
var elphel_wiki_prefix = "http://wiki.elphel.com/index.php?search="

function resize(){
    var w = $(window).width();
    var h = $(window).height();
    if (w>h){
        $("#main").css({width:(h-10)+"px",height:(h-10)+"px"});
        $("#x3d_canvas").css({width:(h-10)+"px",height:(h-10)+"px"});
        $("#bom").css({left:(h)+"px"});
        //$("#thrd").css({left:(h-107)+"px"});
    }else{
        $("#main").css({width:(w-10)+"px",height:(w-10)+"px"});
        $("#x3d_canvas").css({width:(w-10)+"px",height:(w-10)+"px"});
        $("#bom").css({left:(w)+"px"});
        //$("#thrd").css({left:(w-107)+"px"});
    }
}

var resizeTimer;

$(function(){
    
    $(window).resize(function(){
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(resize(),250);
    });
    
    //"model" and some other parameters
    parseURL();
    
    //create and init x3d canvas
    var x3d_cnv = $("<x3d>",{
        id:"x3d_canvas",width:"700px",height:"600px"
    }).css({
        position:"absolute",
        border: "1px solid gray",
        "border-radius": "2px",
        outline: "none"        
    }).addClass("nooutline");
    
    var x3d_cnv_ni = $("<navigationinfo>",{id:"navi",type:"'examine' 'any'"});
    var x3d_cnv_vp = $("<Viewpoint>").attr("fieldOfView",0.2);
    var x3d_cnv_in = $("<inline>",{
        id:"topinline",
        nameSpaceName:NSN,
        url: model,
        onLoad:"document.getElementById('x3d_canvas').runtime.showAll()"
    });
    
    x3d_cnv.append($("<Scene>").append(x3d_cnv_ni).append(x3d_cnv_vp).append(x3d_cnv_in));
        
    $("#main").css({
        position:"absolute",
        width: x3d_cnv.width()+"px",
        height: x3d_cnv.height()+"px"
    });
    
    $("#main").prepend(x3d_cnv);
    
    resize();
    
    var element = document.getElementById('x3d_canvas');

    //on load: showAll()?!
    var showall = 10;
    $(document).load(function(){
        element.runtime.enterFrame = function() {
            if (showall==1) {
                element.runtime.showAll();
                element.runtime.examine();
                run();
            }
            if (showall>0) showall--;
        };
    });
    
    //help button
    var hlp = $("<a href='http://www.x3dom.org/documentation/interaction/'>").addClass("btn btn-primary nooutline btn-sm btn-my").html("?");
    hlp.css({
        position:"absolute",
        right: "3px",
        top: "3px",
        background:"rgba(100,100,100,0.7)",
        border: "1px solid gray",
        padding: "0px 6px 0px 6px"
    });
    
    $("#main").append(hlp);
         
    $("#thrd").css({
        position:"absolute",
        top: "3px",
        right: "27px"
    });

    $("#v1").css({cursor:"pointer"}).click(function(){element.runtime.showAll("posX");});    
    $("#v2").css({cursor:"pointer"}).click(function(){element.runtime.showAll("negX");});

    $("#v3").css({cursor:"pointer"}).click(function(){element.runtime.showAll("posY");});
    $("#v4").css({cursor:"pointer"}).click(function(){element.runtime.showAll("negY");});

    $("#v5").css({cursor:"pointer"}).click(function(){element.runtime.showAll("posZ");});
    $("#v6").css({cursor:"pointer"}).click(function(){element.runtime.showAll("negZ");});
       
});

function run(){
    showBOM();
    bindCanvas();
    resize();
}

function showBOM(){
    
    //var bom = $("<ul>",{id:"bom",class:"list-group"}).css({
    var bom = $("<table>",{id:"bom"}).css({
        position:"absolute",
        top:"5px",
        left:"705px"
    });
    
    var top = $("#topinline");
    //upper case was important
    var parts_unique = top.find("Inline");
    //remove the first element -  because of the specific model structure?
    parts_unique.splice(0,1);
    
    //set default transparency?
    parts_unique.find("Material").attr("transparency",0.1);
    
    parts_unique.each(function(i){
        var part = $(this);
        var tmp_nsn = this.getAttribute("nameSpaceName");
        
        //find secondary appearances
        var sublist = top.find("[USE="+tmp_nsn+"]");
        var ele_sublist = "";
        
        var btn_subpart = false;
        
        ele_ul = $("<ul>",{class:"dropdown-menu","data-toggle":"dropdown"}).css({padding:"10px","min-width":"100px",border:"1px solid rgba(50,50,50,0.5)"});
        btn_part = $("<button>",{class:"btn-part btn btn-default btn-sm btn-success"}).css({"min-width":"100px"}).html(tmp_nsn);
        btn_part.attr("nsn",tmp_nsn);
        btn_part.attr("state","normal");
        ele_sublist = $("<div>",{class:"btn-group"}).append(btn_part).append(
                $("<button>",{class:"dropdown-toggle btn btn-default btn-sm nooutline",
                    "data-toggle":"dropdown",
                    "aria-haspopup":"true",
                    "aria-expanded":"false"
                }).append(
                    $("<span>",{class:"caret"})
                ).append(
                    $("<span>",{class:"sr-only"}).html("Toggle Dropdown")
                )
            );
        ele_sublist.attr("blockpropagation",false);
        
        //toggle all button
        btn_subpart = $("<button>",{class:"btn-subpart btn btn-default btn-sm btn-success",title:"Toggle all"}).css({width:"40px"}).html("all");
        btn_subpart.attr("index",sublist.length);
        btn_subpart.attr("nsn",tmp_nsn);
        btn_subpart.attr("selected",true);
        
        //btn_subpart.click(function(){btn_subpart_click_all($(this),ele_sublist);});
        btn_subpart.click(function(e){
            model_run_cmd(tmp_nsn,"click-int-all");
            e.stopPropagation();
        });
        
        btn_link_to_wiki = $("<a>",{href:elphel_wiki_prefix+tmp_nsn,class:"btn btn-default btn-sm",title:"Elphel Wiki docs"}).html("<span class=\"glyphicon glyphicon-link\" aria-hidden=\"true\"></span>").css({padding:"7px 13px 7px 13px",margin:"6px"});
        
        btn_link_to_wiki.click(function(e){
            window.location.href = $(e.target).attr('href');
        });
        
        ele_ul.append($("<li>").append(btn_subpart.css({display:"inline"})).append(btn_link_to_wiki.css({display:"inline"})).css({padding:"3px","min-width":"100px",width:"100px"}));
        
        //build a list for unique and multiple parts
        for(var j=0;j<=sublist.length;j++){
            btn_subpart = $("<button>",{class:"btn-subpart btn btn-default btn-sm btn-success",title:"Toggle element"}).css({width:"40px"}).html(j+1);
            btn_subpart.attr("index",j);
            //btn_subpart.attr("maxindex",sublist.length);
            btn_subpart.attr("nsn",tmp_nsn);
            btn_subpart.attr("selected",true);
            btn_subpart.click(function(){btn_subpart_click($(this),ele_sublist);});
            
            if (j%5==0) {
                list_el = $("<li>").css({padding:"3px","min-width":"100px",width:"237px"});
                ele_ul.append(list_el);
            }    
            list_el.append(btn_subpart.css({display:"inline",margin:"0px 6px 0px 0px"}));
        }            
        
        ele_sublist.click(function(e){
            if ($(this).attr("blockpropagation")=="true") {
                e.stopPropagation();
            }
            $(this).attr("blockpropagation",false);
        });
        ele_sublist.append(ele_ul);
        
        //var ele = $("<li>",{class:"list-group-item"}).append($(ele_sublist));
        var ele = $("<td>").css({padding:"2px 5px 2px 0px"}).append($(ele_sublist));
                
        if(i%3==0){
            bomtr = $("<tr>");
            bom.append(bomtr);
        }
        bomtr.append(ele);
        
        btn_part.click(function(){
            model_run_cmd(tmp_nsn,"click-ext");
        });
    });
    
    $("body").append(bom);
    
}

var blockclick = false;

function bindCanvas(){
    //whichChoice for Group tag didn't work
    
    $("Switch").each(function(){
        var hmm = $(this);
        var id = hmm.attr("id");
        var pn_arr = id.split(/[_:]/);
        var pn = pn_arr[pn_arr.length-2];
        $(this).attr("nsn",pn);
        $(this).attr("state","normal");
    });
    
    //unblock click
    $("Switch").mousedown(function(){blockclick = false;});
    //block click is the model was rotated
    $("Switch").mousemove(function(){blockclick = true;});
    //click
    $("Switch").click(function(event){
        if (!blockclick){
            var hmm = $(this);
            var id = hmm.attr("id");
            var pn_arr = id.split(/[_:]/);
            var pn = pn_arr[pn_arr.length-2];
            if (event.which==1){
                //fighting multiple click events
                if (pn_arr[pn_arr.length-1]=="0") model_run_cmd(pn,"left-click");
            }
            if (event.which==3){
                //fighting multiple click events
                if (pn_arr[pn_arr.length-1]=="0") model_run_cmd(pn,"right-click");
            }
            console.log("The pointer is over "+hmm.attr("id")+", whichChoice="+hmm.attr("whichChoice")+" render="+hmm.attr("render")+" DEF="+hmm.attr("DEF"));
        }
    });
    
    //$("Switch").attr("onclick","handleClick(event)");
    /*
    $(".btn-subpart").each(function(){
        var index = $(this).attr("index");
        var selected = $(this).attr("selected");
        var nsn = $(this).attr("nsn");
        var some_subpart = document.getElementById(NSN+"__switch_"+nsn+":"+index);
        $(some_subpart).click(function(){
            //$(this).attr("whichChoice",-1);
            console.log("CLIKED: "+$(this).attr("id"));
        });
    });
    */
        
}

function model_run_cmd(name,cmd){
    var state = $("Switch[nsn="+name+"]").attr("state");
    switch(cmd){
        case "right-click":
            //update status to "disabled"
            $("Switch[nsn="+name+"]").attr("state","disabled");
            //whichChoice -1
            $("Switch[nsn="+name+"]").attr("whichChoice",-1);
            //ext buttons - white
            $(".btn-part[nsn="+name+"]").removeClass("btn-success")
                                        .removeClass("btn-primary").css({opacity:"1.0"});
            //int buttons - white
            $(".btn-subpart[nsn="+name+"]").removeClass("btn-success");
            //other buttons - untouched
            break;
        case "left-click":
            if (state=="normal"){
                //other buttons - deselect! 
                
                //other states to normal
                //make others who are visible - almost transparent
                $("Switch").each(function(){
                    $(this).find("Material").attr("transparency",0.9);
                    if (($(this).attr("state")=="selected")||($(this).attr("state")=="superselected")) {
                        $(this).attr("state","normal");
                        $(".btn-part[nsn="+$(this).attr("nsn")+"]").addClass("btn-success").removeClass("btn-primary");
                    }
                    $(".btn-part[nsn="+$(this).attr("nsn")+"]").css({opacity:"1.0"});
                });
                //update status to "selected"
                $("Switch[nsn="+name+"]").attr("state","selected");
                $("Switch[nsn="+name+"]").find("Material").attr("transparency",0.0);
                //ext button - blue
                $(".btn-part[nsn="+name+"]").addClass("btn-primary").removeClass("btn-success").css({opacity:"1.0"});
                //int buttons - green
                $(".btn-subpart[nsn="+name+"]").addClass("btn-success");
            }
            if ((state=="selected")||(state=="superselected")){
                $("Switch").each(function(){
                    $(this).find("Material").attr("transparency",0.1);
                    if (($(this).attr("state")=="selected")||($(this).attr("state")=="superselected")){
                        $(this).attr("state","normal");
                        $(".btn-part[nsn="+$(this).attr("nsn")+"]").addClass("btn-success").removeClass("btn-primary");
                    }
                    $(".btn-part[nsn="+$(this).attr("nsn")+"]").css({opacity:"1.0"});
                });
            }
            break;
        case "click-int-all":
            if (state=="disabled"){
                //update status to "normal"
                $("Switch[nsn="+name+"]").attr("state","normal");
                //whichChoice 0
                $("Switch[nsn="+name+"]").attr("whichChoice",0);
                //ext button - green
                $(".btn-part[nsn="+name+"]").addClass("btn-success");
                //int buttons - green
                $(".btn-subpart[nsn="+name+"]").addClass("btn-success");
                //other buttons - untouched   
            }else{
                //update status to "disabled"
                //whichChoice = -1
                //ext button - white
                //int buttons - white
                //other buttons - untouched
                model_run_cmd(name,"right-click");
            }
            break;
        case "click-ext":
            //disbled, whichChoice=-1?
            if (state=="disabled"){
                //update status to "selected"
                //whichChoice = 0
                //ext button - "blue"
                //int buttons - "green"
                //other buttons
                    //whichChoice = -1?
                        //do not touch
                    //else?
                        //selected?
                            //to normal == green
                model_run_cmd(name,"click-int-all");
            }
            if (state=="selected"){
                //others - switch to normal, make transparent
                $("Switch").each(function(){
                    $(this).find("Material").attr("transparency",1.0);                    
                    if ($(this).attr("state")=="selected") {
                        $(this).attr("state","normal");
                        $(".btn-part[nsn="+$(this).attr("nsn")+"]").addClass("btn-success").removeClass("btn-primary");
                    }
                    if ($(this).attr("state")!="disabled") $(".btn-part[nsn="+$(this).attr("nsn")+"]").css({opacity:"0.5"});
                });
                
                $("Switch[nsn="+name+"]").attr("state","superselected");
                $("Switch[nsn="+name+"]").find("Material").attr("transparency",0.0);
                
                $(".btn-part[nsn="+name+"]").removeClass("btn-success").addClass("btn-primary").css({opacity:"1.0"});
                    //selected?
                        // superselected
                        // update status to superselected
                        // all white? but not permanent? transparent?
                
                //superselected?
                        // update status to normal
                        // all normal?
                
                //normal?
                        // update status to selected
                        // all normal?   
            }
            if (state=="normal"){
                model_run_cmd(name,"left-click");
            }
            if (state=="superselected"){
                $("Switch").each(function(){
                    $(this).find("Material").attr("transparency",0.1);
                    if (($(this).attr("state")=="selected")||($(this).attr("state")=="superselected")) {
                        $(this).attr("state","normal");
                        $(".btn-part[nsn="+$(this).attr("nsn")+"]").addClass("btn-success").removeClass("btn-primary");
                    }
                    $(".btn-part[nsn="+$(this).attr("nsn")+"]").css({opacity:"1.0"});
                });
                model_run_cmd(name,"click-int-all");
            }
            break; 
        default: 
            return false;
    }
}

function handleClick(event){
    console.log(event.hitPnt);
    console.log($(this));
}

function btn_subpart_click(subpart,sublist){
    var index = subpart.attr("index");
    var selected = subpart.attr("selected");
    var nsn = subpart.attr("nsn");
    var some_subpart = document.getElementById(NSN+"__switch_"+nsn+":"+index);
    if (selected) {
        $(some_subpart).attr("whichChoice",-1);
        subpart.removeClass("btn-success");
    }else{
        $(some_subpart).attr("whichChoice", 0);
        subpart.addClass("btn-success");
    }
    subpart.attr("selected",!subpart.attr("selected"));
    sublist.attr("blockpropagation",true);
}

function btn_subpart_click_all(subpart,sublist){
    var index = subpart.attr("index");
    var selected = subpart.attr("selected");
    var nsn = subpart.attr("nsn");
    for(var i=0;i<=index;i++){
        var some_subpart = document.getElementById(NSN+"__switch_"+nsn+":"+i);
        if (selected) {
            $(some_subpart).attr("whichChoice",-1);
            subpart.removeClass("btn-success");
        }else{
            $(some_subpart).attr("whichChoice", 0);
            subpart.addClass("btn-success");
        }
    }
    subpart.attr("selected",!subpart.attr("selected"));
    sublist.attr("blockpropagation",true);
}

function btn_subpart_enableAll(){
    $(".btn-subpart").each(function(){
        var index = $(this).attr("index");
        var selected = $(this).attr("selected");
        var nsn = $(this).attr("nsn");
        var some_subpart = document.getElementById(NSN+"__switch_"+nsn+":"+index);
        $(some_subpart).attr("whichChoice","0");
    });
}

function parseURL() {
  var parameters=location.href.replace(/\?/ig,"&").split("&");
  for (var i=0;i<parameters.length;i++) parameters[i]=parameters[i].split("=");
  for (var i=1;i<parameters.length;i++) {
    switch (parameters[i][0]) {
      case "model": model = parameters[i][1];break;
    }
  }
  console.log("Opening model: "+model);
}
