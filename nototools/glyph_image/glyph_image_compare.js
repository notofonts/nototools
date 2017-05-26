// notodiff image layout

var glyphdiff = {
  'order': { 'std': null, 'sim': null },
  'lock': false,
  'simlimit': 100,
  'image': -1 }

function setCurrentImage(i) {
  var im_div = createImageDiv(i, 1)
  im_div.style.margin="0 auto"
  im_div.id = 'image'

  var data_div = createDataDiv(i)

  var btn = document.createElement('input')
  btn.type = 'checkbox'
  btn.id = 'img_lock'
  btn.checked = glyphdiff.lock
  btn.onclick = function() {
    glyphdiff.lock = btn.checked
  }

  var ref_div = document.getElementById('ref')

  while (ref_div.firstChild) {
    ref_div.removeChild(ref_div.firstChild)
  }
  ref_div.appendChild(data_div)
  ref_div.appendChild(im_div)
  ref_div.appendChild(btn)
  glyphdiff.image = i
}

function setVisibleCount(count) {
  var count_msg = document.getElementById('count_msg')
  count_msg.innerHTML = 'Showing ' + count + ' glyph comparisons.'
}

function resetVisibility() {
  var visible_count = 0
  for (var i = 0; i < glyphdiff.order.std.length; ++i) {
    var div = glyphdiff.order.std[i]
    if (image_data[i][1] <= glyphdiff.simlimit) {
      visible_count += 1
      div.style.display = 'inline-block'
    } else {
      div.style.display = 'none'
    }
  }
  setVisibleCount(visible_count)
}

function setSimilarityLimit(lim) {
  if (lim == glyphdiff.simlimit) {
    return;
  }
  glyphdiff.simlimit = lim
  resetVisibility()
}

function lockImage(lock) {
  if (lock != glyphdiff.lock) {
    toggleImageLock()
  }
}

function toggleImageLock() {
  var btn = document.getElementById('img_lock')
  btn.click()
}

function createImageDiv(i, scale) {
  var name = image_data[i][0]
  var image_path = image_dir + '/' + name
  var image_title = name.substring(0, name.length - 4)

  var img = document.createElement('img')
  img.className = 'im'
  // set onload before setting img.src
  img.onload = function() {
    this.width = this.naturalWidth / scale
    this.height = this.naturalHeight / scale
  }
  img.src = image_path
  img.setAttribute('data-image_ix', i)

  var para = document.createElement('p')
  para.appendChild(document.createTextNode(image_title))
  para.className = 'ti'
  var div = document.createElement('div')
  div.className = 'dv'
  div.appendChild(img)
  div.appendChild(para)
  div.onmouseover = function() {
    if (!glyphdiff.lock) {
      setCurrentImage(i)
    }
  }
  div.onclick = function() {
    if (i == glyphdiff.image) {
      toggleImageLock()
    } else {
      setCurrentImage(i)
      lockImage(true)
    }
  }
  return div
}

function createDataDiv(i) {
  var div = document.createElement('div')
  div.id = 'data'
  var table_lines = ["<table>", "<col align='right'>", "<col align='left'>"]
  function add_row(name, val) {
    table_lines.push("<tr><th>" + name + "<td>" + val)
  }
  var data = image_data[i]
  var similarity = data[1]
  var base_ix = data[2]
  var base_adv = data[3]
  var base_cp = data[4]
  var base_gname = data[5]
  var target_ix = data[6]
  var target_adv = data[7]
  var target_cp = data[8]
  var target_gname = data[9]

  function unistr(val) {
    str = val.toString(16).toUpperCase()
    if (str.length < 4) {
      str = ('0000' + str).substr(-4)
    }
    return str
  }

  if (base_cp == target_cp) {
    if (base_cp != -1) {
      table_lines.push('<tr><td colspan=2>' + cp_data[base_cp])
      add_row('cp', unistr(base_cp))
    }
  } else {
    if (base_cp != -1) {
      table_lines.push('<tr><td colspan=2>' + cp_data[base_cp])
      add_row('base cp', unistr(base_cp))
    }
    if (target_cp != -1) {
      table_lines.push('<tr><td colspan=2>' + cp_data[target_cp])
      add_row('target cp', unistr(target_cp))
    }
  }
  add_row('similarity', similarity)
  if (base_ix == target_ix) {
    add_row('gid', base_ix)
  } else {
    if (base_ix != -1) {
      add_row('base gid', base_ix)
    }
    if (target_ix != -1) {
      add_row('target gid', target_ix)
    }
  }
  if (base_ix != -1 && target_ix != -1 && base_adv == target_adv) {
    add_row('adv', base_adv)
  } else {
    if (base_ix != -1) {
      add_row('base adv', base_adv)
    }
    if (target_ix != -1) {
      add_row('target adv', target_adv)
    }
  }
  table_lines.push("</table>")
  div.innerHTML = table_lines.join('\n')
  return div
}

function initFilter() {
  var input = document.getElementById('filter')
  input.onchange = function() {
    var v = parseInt(input.value)
    setSimilarityLimit(v)
  }
}

function initSort() {
  var sort = document.getElementById('sort')
  sort.onchange = function() {
    reorderImages()
  }

  var sort_order = document.getElementById('sort_order')
  sort_order.onclick = function() {
    sort_order.value = sort_order.value == 'Asc' ? 'Dsc' : 'Asc'
    reorderImages()
  }
}

function reorderImages() {
  var key = document.getElementById('sort').value
  var images = key == 0 ? glyphdiff.order.std : glyphdiff.order.sim
  var asc = document.getElementById('sort_order').value == 'Asc'

  var df = document.createDocumentFragment()
  for (var i = 0; i < images.length; i++) {
    ix = asc ? i : images.length - 1 - i
    df.appendChild(images[ix])
  }
  var parent = document.getElementById('main')
  parent.insertBefore(df, parent.firstChild)
}

function generateImageOrders(stdorder) {
  var sim_ix_order = new Array(image_data.length)
  for (var i = 0; i < image_data.length; ++i) {
    sim_ix_order[i] = i
  }
  sim_ix_order.sort(function(a, b) {
    return image_data[a][1] - image_data[b][1] || a - b
    })
  var simorder = new Array(image_data.length)
  for (var i = 0; i < image_data.length; ++i) {
    simorder[i] = stdorder[sim_ix_order[i]]
  }
  glyphdiff.order.std = stdorder
  glyphdiff.order.sim = simorder
}

function generateImageDivs(scale) {
  var imageDivs = new Array(image_data.length)
  for (var i = 0; i < image_data.length; ++i) {
    imageDivs[i] = createImageDiv(i, scale)
  }
  return imageDivs
}

function init() {
  initFilter()
  initSort()
  generateImageOrders(generateImageDivs(4))
  reorderImages()
  setVisibleCount(glyphdiff.order.std.length)
  setCurrentImage(0)
}
