FROM ubuntu:latest

# TODO: vim should be optional here
RUN apt-get update && \
    apt-get install -y vim g++ gcc python2 wget subversion git gawk && \
    mkdir -p app/

WORKDIR /app

RUN mkdir -p modules && mkdir -p chem_data

WORKDIR /app/chem_data

# TODO: probably just need git here
RUN svn --non-interactive --trust-server-cert co https://github.com/phenix-project/geostd/trunk geostd && \
    svn --non-interactive --trust-server-cert co https://github.com/rlabduke/mon_lib.git/trunk mon_lib && \
    svn --non-interactive --trust-server-cert export https://github.com/rlabduke/reference_data.git/trunk/Top8000/Top8000_rotamer_pct_contour_grids rotarama_data && \
    svn --non-interactive --trust-server-cert --force export https://github.com/rlabduke/reference_data.git/trunk/Top8000/Top8000_ramachandran_pct_contour_grids rotarama_data && \
    svn --non-interactive --trust-server-cert co https://github.com/rlabduke/reference_data.git/trunk/Top8000/Top8000_cablam_pct_contour_grids cablam_data && \
    svn --non-interactive --trust-server-cert co https://github.com/rlabduke/reference_data.git/trunk/Top8000/rama_z rama_z

WORKDIR /app

RUN svn --quiet --non-interactive --trust-server-cert export https://github.com/cctbx/cctbx_project.git/trunk/libtbx/auto_build/bootstrap.py

RUN python2.7 bootstrap.py --builder=molprobity --use-conda --nproc=$(nproc)
