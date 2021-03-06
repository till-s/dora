var localStoragePrefix="";

function isCollapsed( n ) {
    return ! n.classList.contains("active");
}

function gather(l, n) {
  var cc  = n.childNodes;
  var len = cc.length, i;
  //console.log("Gather " + cc.length + " nodes");
  for ( i = 0; i < len; i++ ) {
	  if ( cc[i].nodeType == 1 ) {
		  // ELEMENT
		  if ( cc[i].classList.contains("leaf") ) {
              if ( ! cc[i].classList.contains("WO") ) {
			      l.push( cc[i] );
              }
		  } else if ( cc[i].className !== "nested" || ! isCollapsed( cc[i] ) ) {
			  gather( l, cc[i] );
		  }
	  }
  }
}

function findUpDir( nod ) {
	if ( null == nod ) {
		return nod;
	}
	do {
		nod = nod.parentNode;
		if ( null == nod || null == nod.classList )
			return null;
	} while ( ! nod.classList.contains("dir") );
	if ( nod.id == "theTreeTop" ) {
		return null;
	}
	return nod;
}

function assemblePath( nod ) {
	var l  = [];
	var up = findUpDir( nod );
	while ( up != null ) {
		nod = up.querySelector("button.dropbutton");
		l.push( nod.innerText );
		up = findUpDir( up );
	}
    l.push("");
	return l.reverse().join('/');
}

function bpress() {
var l = [], i;
  gather(l, document.body);
  for (i=0; i<l.length; i++ ) {
    console.log( l[i] );
  }
}

function getNested(el) {
    return el.parentElement.querySelector(".nested");
}

function id2Numeric(id) {
	return parseInt(id.match("[0-9]+")[0]);
}

function subsUnsubs(subs, nodList) {
	if ( nodList.length > 0 ) {
		var i;

		var lid = new Array( nodList.length );

		if ( subs ) {
			for (i=0; i<nodList.length; i++ ) {
				nodList[i].value = "";
				lid[i] = id2Numeric(nodList[i].id);
			}
			cmd = "subscribe";
		} else {
			for (i=0; i<nodList.length; i++ ) {
				lid[i] = id2Numeric(nodList[i].id);
			}
			cmd = "unsubscribe";
		}

		window.treeSocket.emit(cmd, JSON.stringify( lid ) );
	}
}

function changeSubscription(subs, nod) {

	var l   = [];
	var cmd;

	gather(l, nod);

	subsUnsubs(subs, l);

}

function toggleCaret() {
	if ( event.target != this )
		return;
	var nn = getNested( this );
    var cmd;
	if ( nn.classList.contains("active") ) {
		localStorage.removeItem( localStoragePrefix + "active_" + nn.id);
        cmd = false;
	} else {
		localStorage.setItem( localStoragePrefix + "active_" + nn.id,"true");
        cmd = true;
	}
    dropAllDown( null );
	nn.classList.toggle("active");
	this.classList.toggle("caret-down");

	changeSubscription( cmd, nn );
}

function isHexFmt( el ) {
	var chkboxes = el.parentElement.parentElement.getElementsByClassName("hexFmt");
    if ( chkboxes.length > 0 && chkboxes[0].checked ) {
		return true;
	}
	return false;
}

function updateVal_1(el, isHex, val)
{
	if ( val != val ) {
		// bail if NAN
		return;	
	}
	if ( isHex ) {
		el.value = "0x" + val.toString(16);
	} else {
		el.value = val;
	}
}

function updateVal( el ) {
	if ( typeof(el.cachedValue) != "undefined" ) {
		updateVal_1( el, isHexFmt( el ), el.cachedValue );
		if ( el.updateValCallback ) {
			el.updateValCallback( el );
		}
	}
}

function flipHex( chkbox ) {
	var txt = chkbox.parentElement.parentElement.getElementsByClassName("int")[0];
	var val = parseInt( txt.value, 0 );

	updateVal_1( txt, chkbox.checked, val );
}

function storeHex( chkbox ) {
	if ( chkbox.checked != chkbox.classList.contains("checked") ) {
		localStorage.setItem( localStoragePrefix + "checked_" + chkbox.id, chkbox.checked );
console.log("storing hex " + chkbox.id + ": " + chkbox.checked);
	} else {
		localStorage.removeItem( localStoragePrefix + "checked_" + chkbox.id );
console.log("deleting hex " + chkbox.id);
	}
}

function restoreHex( chkbox ) {
	var val = localStorage.getItem( localStoragePrefix + "checked_" + chkbox.id );
console.log("restoring hex " + chkbox.id + ": " + val);
	if ( val != null ) {
		chkbox.checked = (val.toLowerCase() == 'true');
	}
}

function dropThisDown( el ) {
	while ( el != null ) {
		if ( el.classList.contains("dropdown-content") ) {
			el.classList.remove("show");
			return;
		}
		el = el.parentElement;
	}
}

function dropAllDown( butNot ) {
	var alldrops = document.getElementsByClassName("dropdown-content");
	var i;
	for ( i=0; i < alldrops.length; i++ ) {
		if ( butNot == null || alldrops[i] != butNot ) {
			dropThisDown( alldrops[i] );
		}
	}
}

function postSaveConfig(pathUrl, templateYaml) {
		$.post(pathUrl, templateYaml, function(data) {
			var d = JSON.parse( data );
			e = d["error"];
			if ( e ) {
				alert("Save Configuration Failed: " + e);
			} else {
				if ( typeof(d["yaml"]) == "string" ) {
					var a = document.createElement("a");
					var blob   = new Blob( [ d["yaml"] ],
                                           { type: "application/x-yaml" }
                                         );
					var url    = URL.createObjectURL( blob );
					a.href     = url;
					a.download = "config.yaml";
					document.body.appendChild( a );
					a.click();
					a.parentElement.removeChild( a );
					URL.revokeObjectURL( url );
				}
			}
		});
}

function connectEvents() {

    console.log(document.domain);
    console.log(location.port);

	var toggler = document.getElementsByClassName("caret");

	var i;
	for (i = 0; i < toggler.length; i++) {

		var nn = getNested(toggler[i]); 
		if ( "true" == localStorage.getItem( localStoragePrefix + "active_"+nn.id) ) {
			nn.classList.toggle("active"); 
			toggler[i].classList.toggle("caret-down");
		}

	}

	var checkboxes = document.getElementsByClassName("hexFmt");
	for ( i=0; i < checkboxes.length; i++ ) {
		restoreHex( checkboxes[i] );
	}

	window.treeSocket = new io();


	window.treeSocket.on('connect', function() {
		changeSubscription(true, document.body);
	});

	window.treeSocket.on('disconnect', function() {
		console.error('Chat socket closed unexpectedly');
		var l = [], i;
		gather(l, document.body);
		for (i=0; i<l.length; i++ ) {
			var el = document.getElementById( l[i].id );
			el.value = "";
		}
	});

    window.treeSocket.on('update', function(data) {
        var dd = JSON.parse( data );
        for (i=0; i<dd.length; i++) {
			var el     = document.getElementById( dd[i][0] );
            var newVal = dd[i][1];
/*
			if (       typeof( el.cachedValue ) == "undefined"
			      || (     typeof( newVal         ) != "undefined"
                       &&  newVal != el.cachedValue ) ) */ {
	            el.cachedValue = newVal;
				if ( document.activeElement != el ) {
					updateVal( el );
				}
			}
		}
    });

	$(document).on("change","input.leaf,select.leaf",function() {

        var v = this.value;

		if ( this.classList.contains("int") ) {
			v = parseInt( this.value, 0 );			

			if ( v != v ) {
				alert( "Invalid Numerical Entry (integer)" );
				if ( typeof( this.cachedValue ) != "undefined" ) {
					this.value = this.cachedValue;
				}
				return;
			}
		} else if ( this.classList.contains("float") ) {
			v = parseFloat( this.value );			

			if ( v != v ) {
				alert( "Invalid Numerical Entry (float)" );
				if ( typeof( this.cachedValue ) != "undefined" ) {
					this.value = this.cachedValue;
				}
				return;
			}
		}
		// So this goes into the readback when blurred
		this.cachedValue = v;
		if ( this.updateValCallback ) {
			this.updateValCallback( this );
		}
		var l = [];
		var p = [];
		p.push( id2Numeric( this.id ) );
		p.push( v                     );
		l.push( p                     );
		window.treeSocket.emit( "setVal", JSON.stringify( l ) );
		if ( isHexFmt( this ) ) {
			updateVal_1( this, true, v );
		}
	});

	$(document).on("change", ".hexFmt", function() {
		flipHex ( this );
		storeHex( this );
	});

	$(document).on("click", ".caret", toggleCaret);

	$(document).on("click", "button.cmd", function() {
		window.treeSocket.emit( "setVal", "[ [ " + id2Numeric( this.id ) + ", 1 ] ]" );
	});

	$(document).on("blur",  ".leaf", function() {
		if ( typeof(this.cachedValue) != "undefined" ) {
			updateVal( this );
		}
	});

	$(document).on("mouseover", ".toolTipper",
		function() {
			//console.log("OVER");
			if ( typeof(this.tooltipTimer) != "undefined" && this.tooltipTimer ) {
				clearTimeout( this.tooltipTimer );
				this.tooltipTimer = null;
			}
			var tip = this.parentNode.getElementsByClassName("tooltip")[0];
			if ( ! tip && this.parentNode.parentNode ) {
				tip = this.parentNode.parentNode.getElementsByClassName("tooltip")[0];
			}
			this.tooltipTimer = setTimeout( function( tip ) {
					//console.log("TIMEOUT: " + tip);
					if ( ! tip.classList.contains("show") ) {
						tip.classList.add("show")
					}
			}, 2000, tip);
			//console.log("set timeout: " + this.tooltipTimer);
	});
	$(document).on("mouseout", ".toolTipper",
		function() {
			var tip = this.parentNode.getElementsByClassName("tooltip")[0];
			var timer = this.tooltipTimer;
			if ( timer ) {
				clearTimeout( timer );
				this.tooltipTimer = null;
			}
			tip.classList.remove("show");
	});

	$(document).on("click", ".dropbutton", function() {
        dropd = this.parentElement.getElementsByClassName("dropdown-content");
		// Hide all others
		dropAllDown( dropd[0] );
        dropd[0].classList.toggle("show");
	});

	$(document).on("click", ".saveConfig", function( event ) {
		event.preventDefault();
		postSaveConfig( this.href, "" );
		dropThisDown( this );
	});

	$(document).on("click", ".loadConfig,.saveConfigFromTemplate", function() {
		var fl = this.files;
		this.value = null;
		this.files = fl;
	});

	$(document).on("change", ".saveConfigFromTemplate", function() {
        var lnk    = this.parentElement.getElementsByTagName("a");
		var path   = lnk[0].href;
		var reader = new FileReader();

		//console.log("from template; path " + path);

		reader.addEventListener('loadend', function(event) {
			if ( event.type == "loadend" ) {
				postSaveConfig( path, this.result );
			} else if ( even.type === "error" ) {
				alert("Unable to load template file: " + event.error);
			}
		});

		reader.readAsText( this.files[0] );
		dropThisDown( this );
	});

	$(document).on("change", ".loadConfig", function() {
			var path   = assemblePath( this.parentNode );	
			var reader = new FileReader();
console.log("loading config ", path);

			reader.addEventListener('loadend', function(event) {
					if ( event.type === "loadend" ) {
						$.post("loadConfig?path=" + encodeURIComponent(path) + "&json=True",
							this.result,
							function(data) {
								var d = JSON.parse( data );
								//console.log("POST Received " + JSON.parse( data ));
								e = d["error"];
								if ( e ) {
									alert("Load Configuration Failed: " + e);
								} else {
									alert( d["result"] + " Values Successfully Written" );
								}
							});
					} else if ( event.type === "error" ) {
						alert("Unable to load file: " + event.error);
					}
				});

			reader.readAsText( this.files[0] );
			dropThisDown( this );
		});
}
