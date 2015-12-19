/*
FILE NAME  : viewmodel.js
DESCRIPTION: x3d viewer
REVISION: 1.00
AUTHOR: Oleg Dzhimiev <oleg@elphel.com>
LICENSE: AGPL v3+, see http://www.gnu.org/licenses/agpl.txt
Copyright (C) 2015 Elphel, Inc.
*/

var model = "Undefined";
var NSN = "m";
var elphel_wiki_prefix = "http://wiki.elphel.com/index.php?search="
var nobuttons = false;
var animate = false;
var settings_file = "settings.xml";
var path = "";
var inherited_parameters = "";

function resize(){
    console.log("resize");
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

var moveTimeSet = 0;
var moveTimeStamp;

var showdefault = 0;

var load_counter = 0;
var load_limit = 1;
/*
$(function(){
   prerun();
});
*/
function prerun(){
    $(window).resize(function(){
        clearTimeout(resizeTimer);
        resizeTimer = window.setTimeout(resize(),250);
    });
    
    //"model" and some other parameters
    parseURL();
        
    //create and init x3d canvas
    var x3d_cnv = $("<x3d>",{
        id:"x3d_canvas",width:"700px",height:"600px",showLog:"false"
    }).css({
        position:"absolute",
        border: "1px solid gray",
        "border-radius": "2px",
        outline: "none"        
    }).addClass("nooutline");
    
    $("#main").prepend(x3d_cnv);
    
    x3d_cnv.click(function(){
        stop_animation();
    });
    
    var x3d_cnv_ni = $("<NavigationInfo>",{id:"navi",type:"'examine' 'any'",speed:"15",headlight:"true"});
    
    var x3d_cnv_vp = $("<Viewpoint>").attr("fieldOfView","0.202");
    
    var x3d_cnv_in = $("<inline>",{
        id:"topinline",
        nameSpaceName:NSN,
        url: model
        //onLoad:"document.getElementById('x3d_canvas').runtime.showAll()"
    });
        
    var x3d_cnv_trans = $("<Transform id='anima' DEF='ball'>");
    
    var x3d_cnv_anim = $("\
<timeSensor DEF='time' cycleInterval='50' loop='true'></timeSensor>\
<orientationInterpolator DEF='move' key='0 0.5 1' keyValue='0 0 1 0 0 0 1 3.14159 0 0 1 6.28317'></orientationInterpolator>\
<Route fromNode='time' fromField ='fraction_changed' toNode='move' toField='set_fraction'></Route>\
<Route fromNode='move' fromField ='value_changed' toNode='ball' toField='set_rotation'></Route>\
");
    
    x3d_cnv_trans.append(x3d_cnv_in);
    
    if (animate){
        x3d_cnv_trans.append(x3d_cnv_anim);
    }
    
    var scene = $("<Scene>");
    scene.append(x3d_cnv_trans);
    x3d_cnv.append(scene);
            
    var settings = $("<div>").load(settings_file,function(response,status,xhr){
        if (xhr.status==200){
            var xml = $.parseXML(response);
            x3d_cnv_ni = $(xml).find("NavigationInfo");
            x3d_cnv_vp = $(xml).find("Viewpoint");
            showdefault = 1;
        }
        scene.prepend(x3d_cnv_vp).prepend(x3d_cnv_ni);
    });
    
    $("#main").css({
        position:"absolute",
        width: x3d_cnv.width()+"px",
        height: x3d_cnv.height()+"px"
    });
    
    var element = document.getElementById('x3d_canvas');

    //on load: showAll()?!
    //required minimum?
    
    var showall = 1;
        
    $(document).load(function(){
        element.runtime.enterFrame = function() {
            if (showall==1) {
                element.runtime.examine();
                element.runtime.showAll("negY");
                if (showdefault) element.runtime.resetView();
                run();
            }
            if (showall>0) showall--;
        };
    });
    
    //help button
    //var hlp = $("<a href='http://www.x3dom.org/documentation/interaction/'>").addClass("btn btn-primary nooutline btn-sm btn-my").html("?");
    var hlp = $("<div>").addClass("btn btn-primary nooutline btn-sm btn-my").html("?");
    hlp.css({
        position:"absolute",
        right: "3px",
        top: "3px",
        background:"rgba(100,100,100,0.7)",
        border: "1px solid gray",
        padding: "0px 6px 0px 6px"
    });
    
    var hlp_text = $("<div>",{id:"help-text"}).css({
        position:"absolute",
        top:"2px",
        right:"2px",
//         width:"800px",
//         height:"600px",
        "border-radius":"2px",
        border: "1px solid gray",
        color:"white",
        "font-size":"1.2em",
        padding:"10px 10px 10px 10px",
        background:"rgba(50,50,50,0.9)",
        display:"none"
    });
    
    hlp_text.html("\
<table>\
<tr>\
    <td>Display area:<td>\
</tr>\
<tr>\
    <td valign='top'>&nbsp;&nbsp;&nbsp;&nbsp;<b>&#8226; left-click:</b></td>\
    <td valign='top'>select/deselect part and its copies</td>\
</tr>\
<tr>\
    <td valign='top'>&nbsp;&nbsp;&nbsp;&nbsp;<b>&#8226; left-click + move:</b></td>\
    <td valign='top'>rotate</td>\
</tr>\
<tr>\
    <td valign='top'>&nbsp;&nbsp;&nbsp;&nbsp;<b>&#8226; right-click:</b></td>\
    <td valign='top'>hide part and its copies</td>\
</tr>\
<tr>\
    <td valign='top'>&nbsp;&nbsp;&nbsp;&nbsp;<b>&#8226; right-click + move:</b></td>\
    <td valign='top'>zoom</td>\
</tr>\
<tr>\
    <td valign='top'>&nbsp;&nbsp;&nbsp;&nbsp;<b>&#8226; middle-click + move:</b></td>\
    <td valign='top'>drag</td>\
</tr>\
<tr>\
    <td valign='top'>&nbsp;&nbsp;&nbsp;&nbsp;<b>&#8226; dbl-left-click:</b></td>\
    <td valign='top'>set center of rotation but <span style='color:rgba(255,100,100,1)'><b>interferes with left-click</b></span></td>\
</tr>\
<tr>\
    <td valign='top'>&nbsp;&nbsp;&nbsp;&nbsp;<b>&#8226; dbl-middle-click:</b></td>\
    <td valign='top'>set center of rotation</td>\
</tr>\
<tr>\
    <td>Side buttons (if enabled):</td>\
</tr>\
<tr>\
    <td>&nbsp;&nbsp;&nbsp;&nbsp;<b>&#8226; <span style='padding:1px 5px;background:green;border-radius:2px 0px 0px 2px;'>abc</span><span style='padding:1px 5px;background:white;border-radius:0px 2px 2px 0px;color:black;'>&#x25BE;</span>&nbsp;<b>:</b></td>\
    <td><b>abc</b> = Part Number</td>\
</tr>\
<tr>\
    <td>&nbsp;&nbsp;&nbsp;&nbsp;<b>&#8226; <span style='padding:1px 5px;background:green;border-radius:2px 0px 0px 2px;'>abc</span> left-click:</b></td>\
    <td>select / single / hide / delesect</td>\
</tr>\
<tr>\
    <td>&nbsp;&nbsp;&nbsp;&nbsp;<b>&#8226; dropdown</b> <span style='padding:1px 5px;background:green;border-radius:2px;'>all</span> <b>:</b></td>\
    <td>hide/show part and its copies</td>\
</tr>\
<tr>\
    <td>&nbsp;&nbsp;&nbsp;&nbsp;<b>&#8226; dropdown</b> <span style='padding:1px 5px;background:green;border-radius:2px;'>1</span> <b>:</b></td>\
    <td>hide/show single part or copy</td>\
</tr>\
<tr>\
    <td>X3DOM controls help:</td>\
</tr>\
<tr>\
    <td>&nbsp;&nbsp;&nbsp;&nbsp;<b>&#8226; <a href='http://www.x3dom.org/documentation/interaction/' style='color:white'><img src='http://www.x3dom.org/wp-content/themes/x3domnew/x3dom_logo.png' style='background:rgba(250,250,250,0.8);height:25px;padding:3px'/> www.x3dom.org</a></td>\
</tr>\
<tr>\
    <td>Source code:</td>\
</tr>\
<tr>\
    <td>&nbsp;&nbsp;&nbsp;&nbsp;<b>&#8226; <a href='https://github.com/Elphel/freecad_x3d' style='color:white'><img src='http://blog.elphel.com/wp-content/themes/pixelgreen/images/blog-logo.png' style='height:25px;'/> Elphel <img src='https://github.com/fluidicon.png' style='height:25px;'/> github.com</a></td>\
</tr>\
</table>\
");
    
    
    hlp.click(function(){
        hlp_text.css({display:""});
    });
    
    hlp_text.click(function(){
        $(this).css({display:"none"});
    });
    
    $("#main").append(hlp).append(hlp_text);
    
    //info popup
    var info = $("<div>",{id:"info"}).css({
        position:"absolute",
        bottom:"3px",
        right:"3px",
        "border-radius":"2px",
        border: "1px solid gray",
        color:"white",
        "font-size":"1.2em",
        padding:"10px 10px 10px 10px",
        background:"rgba(50,50,50,0.9)"
    });
    
    $("#main").append(info);
    
    rst_model = $("<button>",{id:"reset_model"}).addClass("btn-my btn nooutline").html("reset model").css({
        position: "absolute",
        top: "3px",
        left: "3px",
        cursor:"pointer"
    });
    
    rst_model.click(function(){
        model_run_cmd("reset","reset");
        btn_subpart_enableAll();
        model_init();
        //element.runtime.showAll("negY");
        //if (showdefault) element.runtime.resetView();
        //element.runtime.resetView();
        if (animate) start_animation();
    });
    
    $("#main").append(rst_model);

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
    
    $("#v7").css({cursor:"pointer"}).click(function(){element.runtime.resetView();});
       
}

function model_init(){
    removeBOM();
    showBOM();
    resize();
    unbindCanvas();
    bindCanvas();
}

var block_load_events = false;

function run(){
    console.log("run()");
    var inlines = $.find("Inline");
    console.log("Found inlines: "+inlines.length);
    load_limit = inlines.length;
    load_counter = 0;
    
    if (load_limit==1){
        tmp_inline = $(inlines[0]);
        tmp_inline.load(function(){
            run2();
        });
    }    
}

function run2(){
    console.log("run2()");
    var inlines = $.find("Inline");
    console.log("Found new inlines: "+(inlines.length-1));
    load_limit = inlines.length;
    
    for(var i=0;i<inlines.length;i++){
        tmp_inline = $(inlines[i]);
        tmp_inline.load(function(){
            load_counter++;
            console.log("Loaded "+load_counter);
            var progress_element = $.find("strong");
            var progress_counter = $(progress_element).html();
            progress_counter = progress_counter.split(" ");
            console.log("x3dom counter = "+progress_counter[1]);
            if (!block_load_events){
                if (load_counter==1){
                    console.log("fire init (1)");
                    model_init();
                    //unbindCanvas();
                    //bindCanvas();
                }                              
                if (load_counter==(load_limit-2)){
                    console.log("fire init (limit-2)");
                    model_init();
                    //unbindCanvas();
                    //bindCanvas();
                }              
            }
        });
    }
    if (inlines.length==1) {
        //bindCanvas();
        model_init();
    }
}


function removeBOM(){
    var top = $("#topinline");
    top.find("Inline").off("click");
    top.find("button").off("click");
    top.find("a").off("click");
    $("#bom").remove();
}

function place_camera(){
    
    var top = $("#topinline");
    //get top boundary box position
    var top_groups = top.find("Group");
    
    if (top_groups.length>0){
        var top_group = $(top_groups[0]);
        var top_bboxcenter = top_group.prop('bboxCenter');
        top_bboxcenter = top_bboxcenter.split(" ");
        var top_bboxsize = top_group.prop('bboxSize');
        top_bboxsize = top_bboxsize.split(" ");
        
        console.log("Top group bboxcenter is at");
        console.log(top_bboxcenter);
        
        top_group.parent().prop("translation",(-top_bboxcenter[0])+" "+(-top_bboxcenter[1])+" "+(-top_bboxcenter[2]));
        
        //var fov = $("Viewpoint").attr("fieldOfView");
        var fov = $("Viewpoint").prop("fieldOfView");
        
        console.log("field of view is "+fov);
        
        //(top_bboxsize[1]/2) / l = tg a/2
        fov=fov*0.75;
        var phi = -0.7;
        
        var boxsize;
        
        boxsize = Math.max(...top_bboxsize);
        
        var view_distance = (boxsize/2)/Math.tan(fov/2);    
        
        var view_elevation = view_distance*Math.tan(phi);
        
        //$("Viewpoint").attr("position","0 "+view_distance+" 0");
        //$("Viewpoint").attr("orientation","-1 0 0 1.57080");
        console.log(view_distance+" "+view_elevation+" "+phi);
        
        $("Viewpoint").attr("position","0 "+view_distance+" "+(view_elevation));
        $("Viewpoint").attr("orientation","-1 0 0 "+(Math.PI/2-phi));
        showdefault = true;
        
        var element = document.getElementById('x3d_canvas');
        if (showdefault) element.runtime.resetView();
        
        var x3d_cnv_ni = $("NavigationInfo");
        x3d_cnv_ni.prop("speed",Math.round(Math.sqrt(view_distance)/5));
        console.log("speed is "+x3d_cnv_ni.prop("speed"));
        
    }
}

function showBOM(){
    console.log("showBOM");    
    //var bom = $("<ul>",{id:"bom",class:"list-group"}).css({
    var bom = $("<table>",{id:"bom"}).css({
        position:"absolute",
        top:"5px",
        left:"105px"
    });
    
    if (nobuttons){
        bom.css({
            display:"none"
        });
    }
    
    var top = $("#topinline");
    place_camera();
    
    //upper case was important
    var parts_unique = top.find("Inline");
    //remove the first element -  because of the specific model structure?
    parts_unique.splice(0,1);
    //console.log("Unsorted");
    //console.log(parts_unique);  
    parts_unique.sort(function(a,b){
        a = $(a).prop("nameSpaceName");
        b = $(b).prop("nameSpaceName");
        if(a > b) {
            return 1;
        } else if(a < b) {
            return -1;
        } else {
            return 0;
        }
    });
    
    //console.log("Sorted");
    //console.log(parts_unique);
    
    //set default transparency?
    parts_unique.find("Material").attr("transparency",0.1);
    parts_unique.find("Material").prop("transparency",0.1);
        
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
        
        btn_link_open = $("<a>",{href:"?"+inherited_parameters+"model="+path+"/"+tmp_nsn+".x3d",class:"btn btn-default btn-sm",title:"Open in new window"}).html("<span class=\"glyphicon glyphicon-open\" aria-hidden=\"true\"></span>").css({padding:"7px 13px 7px 13px",margin:"6px 0px 6px 6px"});
        
        btn_link_open.click(function(e){
            window.location.href = $(this).attr('href');
        });
        
        btn_link_to_wiki = $("<a>",{href:elphel_wiki_prefix+tmp_nsn,class:"btn btn-default btn-sm",title:"Elphel Wiki docs"}).html("<span class=\"glyphicon glyphicon-book\" aria-hidden=\"true\"></span>").css({padding:"7px 13px 7px 13px",margin:"6px"});
        
        btn_link_to_wiki.click(function(e){
            window.location.href = $(this).attr('href');
        });
        
        ele_ul.append($("<li>").append(btn_subpart.css({display:"inline"}))
                               .append(btn_link_open.css({display:"inline"}))
                               .append(btn_link_to_wiki.css({display:"inline"}))
                               .css({padding:"3px","min-width":"100px",width:"150px"}));
        
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

function unbindCanvas(){
    $("Switch").off("mousedown").off("mousemove").off("click");
    var canvas = document.getElementById("x3d_canvas");
    canvas.removeEventListener("touchstart",touchstarted,false);
    canvas.removeEventListener("touchmove",touchmoved,false); 
}

function bindCanvas(){
    //whichChoice for Group tag didn't work
    //$("Switch").on("mousedown").on("mousemove").on("click");
    
    $("Switch").each(function(){
        var hmm = $(this);
        var id = hmm.attr("id");
        var pn_arr = id.split(/[_:]/);
        var pn = pn_arr[pn_arr.length-2];
        $(this).attr("nsn",pn);
        $(this).attr("state","normal");
    });
    
    //unblock click
    $("Switch").mousedown(function(){
        blockclick = false;
    });
    //block click is the model was rotated
    $("Switch").mousemove(function(e){
        //alert(e.which);
        if (e.which==1) {
            blockclick = true;
        }
    });
    
    var canvas = document.getElementById("x3d_canvas");
    canvas.addEventListener("touchstart",touchstarted,false);
    canvas.addEventListener("touchmove",touchmoved,false);
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
}

function touchstarted(){
    stop_animation();
    blockclick = false;
    moveTimeStamp = getTimeStamp(); 
}

function touchmoved(){
    //blockclick = true;
    if ((getTimeStamp()-moveTimeStamp)>100){
        blockclick = true;
    }
}

function stop_animation(){
    $("timeSensor").remove();
    $("orientationInterpolator").remove();
    $("Route").remove();
}

function start_animation(){
    console.log("restart animation");    
    var x3d_cnv_anim = $("\
<timeSensor DEF='time' cycleInterval='50' loop='true'></timeSensor>\
<orientationInterpolator DEF='move' key='0 0.5 1' keyValue='0 0 1 0 0 0 1 3.14159 0 0 1 6.28317'></orientationInterpolator>\
<Route fromNode='time' fromField ='fraction_changed' toNode='move' toField='set_fraction'></Route>\
<Route fromNode='move' fromField ='value_changed' toNode='ball' toField='set_rotation'></Route>\
");
    
    $("#anima").append(x3d_cnv_anim);
}

function getTimeStamp(){
    var d = new Date();
    return d.getTime();
}

function blockclique(){
    blockclick = true;
    //moveTimerSet = false;
}

function unblockclique(){
    blockclick = false;
    //moveTimerSet = false;
}

function update_info(name,state,cmd){
    $("#info").empty();
    switch(cmd){
        case "left-click":
            if (state=="normal"){
                var pn = $("<span>").html(name);
                var open_btn = $("<a>",{
                    id:"info_open",
                    title:"open part in a new window",
                    class:"btn btn-default btn-sm nooutline"    
                }).attr("nsn",name).html("<span class=\"glyphicon glyphicon-open\" aria-hidden=\"true\"></span>").css({
                    padding: "8px 11px 7px 11px",
                    margin: "0px 0px 0px 10px"
                });
                
                open_btn.attr("href","?"+inherited_parameters+"model="+path+"/"+name+".x3d");
                
                var hide_btn = $("<button>",{
                    id:"info_hide",
                    title:"hide parts",
                    class:"btn btn-default btn-danger btn-sm nooutline"    
                }).attr("nsn",name).html("<span class=\"glyphicon glyphicon-remove\" aria-hidden=\"true\"></span>").css({
                    padding: "8px 11px 7px 11px",
                    margin: "0px 0px 0px 10px"
                });
                
                hide_btn.click(function(){
                    model_run_cmd(name,"info-hide-click");
                });
                
                $("#info").append(pn).append($("<span>").append(open_btn)).append($("<span>").append(hide_btn));
            }
            break;
        default: return false;
    }
}

function model_run_cmd(name,cmd){
    var state = "";
    if (name!="reset"){
        state = $("Switch[nsn="+name+"]").attr("state");
        update_info(name,state,cmd);
    }
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
                model_run_cmd(name,"normalize");
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
            case "info-hide-click":
                model_run_cmd(name,"normalize");
                model_run_cmd(name,"right-click");
            break;
        case "normalize":
            $("Switch").each(function(){
                $(this).find("Material").attr("transparency",0.1);
                if (($(this).attr("state")=="selected")||($(this).attr("state")=="superselected")){
                    $(this).attr("state","normal");
                    $(".btn-part[nsn="+$(this).attr("nsn")+"]").addClass("btn-success").removeClass("btn-primary");
                }
                $(".btn-part[nsn="+$(this).attr("nsn")+"]").css({opacity:"1.0"});
            });                
            break;
        case "reset":
            $("Switch").each(function(){
                $(this).attr("whichChoice",0);
                $(this).find("Material").attr("transparency",0.1);
                $(this).attr("state","normal");
                $(".btn-part[nsn="+$(this).attr("nsn")+"]").addClass("btn-success").removeClass("btn-primary");
                $(".btn-part[nsn="+$(this).attr("nsn")+"]").css({opacity:"1.0"});
                $(".btn-subpart[nsn="+$(this).attr("nsn")+"]").addClass("btn-success").attr("selected",true);
            });
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
        $(some_subpart).attr("whichChoice","0").attr("selected",true);
    });
}

function parseURL() {
    var parameters=location.href.replace(/\?/ig,"&").split("&");
    for (var i=0;i<parameters.length;i++) parameters[i]=parameters[i].split("=");
    for (var i=1;i<parameters.length;i++) {
        switch (parameters[i][0]) {
        case "model": model = parameters[i][1];break;
        case "nobuttons": nobuttons = true;break;
        case "animate": animate = true;break;
        //case "settings": settings_file = parameters[i][1];break;
        }
    }
    if (nobuttons) inherited_parameters += "nobuttons&";
    if (animate)   inherited_parameters += "animate&";
    
    var index = model.lastIndexOf("/");
    if (index>0){
        path = model.substr(0,index);
    }
    settings_file = model.slice(0,-3)+"xml";
    console.log("Opening model: "+model);
}
